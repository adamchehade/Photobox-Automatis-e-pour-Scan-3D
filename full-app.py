import sys
import os
import time
import threading
import requests
import cv2
import tempfile
import torch
import numpy as np
import streamlit as st
import plotly.graph_objs as go
import trimesh
from PIL import Image 

# --- CONFIGURATION & PATHS ---
sys.path.append(os.path.join(os.getcwd(), "dust3r"))

SCANS_FOLDER = os.path.join(os.getcwd(), "scans_output")
if not os.path.exists(SCANS_FOLDER):
    os.makedirs(SCANS_FOLDER)

# --- 1. HARDWARE SCANNER CLASS (Singleton) ---
class HardwareScanner:
    def __init__(self):
        self.ESP_IP = "192.168.221.219"
        self.ESP_URL = f"http://{self.ESP_IP}/control"
        self.CAMERA_INDEX = 1  # ⚠️ Ensure this matches your setup (0 or 1)
        self.MOTOR_STEPS_PER_REV = 2048
        self.GEAR_RATIO = 3.0
        self.TIME_PER_STEP = 0.003
        
        # State
        self.running = False
        self.progress = 0
        self.total_images = 0
        self.current_scan_folder = ""
        self.latest_images = []
        self.log_messages = []

    def log(self, msg):
        self.log_messages.append(msg)
        if len(self.log_messages) > 10:
            self.log_messages.pop(0)

    def start_scan_thread(self, num_photos):
        if self.running:
            return
        self.running = True
        self.progress = 0
        self.total_images = num_photos
        self.latest_images = []
        self.log_messages = []
        
        thread = threading.Thread(target=self._scan_sequence, args=(num_photos,))
        thread.start()

    def _scan_sequence(self, num_photos):
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.current_scan_folder = os.path.join(SCANS_FOLDER, timestamp)
            os.makedirs(self.current_scan_folder, exist_ok=True)
            self.log(f"Starting scan: {timestamp}")

            # Math
            total_table_steps = self.MOTOR_STEPS_PER_REV * self.GEAR_RATIO
            steps_per_move = int(total_table_steps / num_photos)
            move_duration = (steps_per_move * self.TIME_PER_STEP) + 1.2

            # --- CAMERA INIT ---
            # Using CAP_DSHOW for Windows compatibility
            cap = cv2.VideoCapture(self.CAMERA_INDEX, cv2.CAP_DSHOW) 
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920) 
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not cap.isOpened():
                self.log(f"Error: Cam {self.CAMERA_INDEX} is busy or not found.")
                self.running = False
                return

            self.log("Warming up camera...")
            time.sleep(2) 

            # Flush buffer
            for _ in range(5):
                cap.read()
                time.sleep(0.05)

            for i in range(num_photos):
                if not self.running: break 

                self.progress = i + 1
                
                # Stabilize image
                for _ in range(6):
                    cap.read()
                    time.sleep(0.05) 

                ret, frame = cap.read()
                if ret:
                    filename = f"img_{i:03d}.jpg"
                    full_path = os.path.join(self.current_scan_folder, filename)
                    cv2.imwrite(full_path, frame)
                    self.latest_images.append(full_path)
                    self.log(f"Captured {filename}")
                else:
                    self.log("Failed to grab frame.")
                
                # Move Motor
                try:
                    requests.get(self.ESP_URL, params={
                        'mode': '4', 'steps': steps_per_move, 'dir': 'cw'
                    }, timeout=1)
                    time.sleep(move_duration)
                except Exception as e:
                    self.log(f"ESP Error: {e}")

            cap.release()
            self.log("Scan Complete.")
        except Exception as e:
            self.log(f"Critical Error: {e}")
        finally:
            self.running = False

@st.cache_resource
def get_scanner():
    return HardwareScanner()

scanner = get_scanner()

# --- 2. DUST3R SETUP ---
@st.cache_resource
def load_dust3r_model():
    try:
        from dust3r.inference import inference
        from dust3r.model import AsymmetricCroCo3DStereo
        
        model_name = "naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AsymmetricCroCo3DStereo.from_pretrained(model_name).to(device)
        return model, device
    except ImportError:
        return None, None

def visualize_point_cloud(points, colors=None):
    if colors is not None and len(colors) == len(points):
        marker_color = colors
    else:
        marker_color = points[:, 2]

    fig = go.Figure(data=[go.Scatter3d(
        x=points[:, 0], y=points[:, 1], z=points[:, 2],
        mode='markers',
        marker=dict(size=2, color=marker_color, opacity=0.8)
    )])
    fig.update_layout(scene=dict(aspectmode='data'), height=600, margin=dict(l=0,r=0,b=0,t=0))
    return fig

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Scanner Hub", layout="wide")
st.title(" Automated PhotoBox")

# Initialize Session State for Camera Toggle
if 'ai_camera_active' not in st.session_state:
    st.session_state.ai_camera_active = False

# Tabs
tab_enhance, tab_scan, tab_recon = st.tabs(["✨ AI Enhancer", "📸 Hardware Scanner", "🧊 3D Reconstruction"])

# ==========================================
# TAB 1: AI ENHANCER (Conditional Camera)
# ==========================================
with tab_enhance:
    st.header(" AI Enhancer")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.info("💡 To use this tab, you must enable the camera below. Turn it OFF when switching to the Hardware Scanner.")
        
        # === THE FIX: TOGGLE SWITCH ===
        # This prevents the camera from being locked when you don't need it
        st.session_state.ai_camera_active = st.toggle("🔴 Activate Camera for AI", value=False)
        
        SERVER_URL = st.text_input("Server URL", "http://192.168.221.66:5005/enhance")
        TIMEOUT_SEC = 180 

    with col_b:
        if st.session_state.ai_camera_active:
            # Camera Input is ONLY rendered if toggle is True
            img_file_buffer = st.camera_input("Take a picture")

            if img_file_buffer is not None:
                st.write("Sending to server...")
                try:
                    bytes_data = img_file_buffer.getvalue()
                    files = {"file": ("capture.jpg", bytes_data, "image/jpeg")}
                    response = requests.post(SERVER_URL, files=files, timeout=TIMEOUT_SEC)

                    if response.status_code == 200:
                        img_array = np.frombuffer(response.content, np.uint8)
                        result_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
                        st.image(result_rgb, caption="Enhanced Result")
                        st.balloons()
                    else:
                        st.error(f"Server Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("📷 Camera is currently released for the Hardware Scanner.")
            st.image("https://placehold.co/600x400?text=Camera+Released", caption="Enable toggle to view camera")

# ==========================================
# TAB 2: HARDWARE SCANNER
# ==========================================
with tab_scan:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Scanner Settings")
        
        # Check if AI Camera is hogging the resource
        if st.session_state.ai_camera_active:
            st.error("⚠️ Camera is locked by AI Tab! Please turn off 'Activate Camera for AI' in the first tab.")
        
        photos_per_turn = st.number_input("Photos per Turn", min_value=4, max_value=100, value=24)
        
        if not scanner.running:
            # Disable button if AI camera is active
            btn_disabled = st.session_state.ai_camera_active
            if st.button(" Start New Scan", type="primary", disabled=btn_disabled):
                scanner.start_scan_thread(photos_per_turn)
                st.rerun()
        else:
            st.warning("Scanner is running...")
            if st.button(" Force Stop"):
                scanner.running = False
                st.rerun()

        st.divider()
        st.code("\n".join(scanner.log_messages), language="text")
        
    with col2:
        st.subheader("Live Progress")
        prog_bar = st.progress(0)
        status_text = st.empty()
        gallery_placeholder = st.empty()

        if scanner.total_images > 0:
            pct = min(scanner.progress / scanner.total_images, 1.0)
            prog_bar.progress(pct)
        
        status_text.write(f"Status: {'Running' if scanner.running else 'Idle'} | Images: {scanner.progress} / {scanner.total_images}")
        
        if scanner.latest_images:
            cols = gallery_placeholder.columns(4)
            recent = scanner.latest_images[-4:]
            for idx, img_path in enumerate(recent):
                cols[idx].image(img_path, caption=os.path.basename(img_path))
        
        if scanner.running:
            time.sleep(1)
            st.rerun()

# ==========================================
# TAB 3: 3D RECONSTRUCTION
# ==========================================
with tab_recon:
    st.header("Generate or View 3D Models")
    
    data_source = st.radio("Select Source:", ["Upload Images", "Use Last Scan", "Load Existing 3D Model"])
    image_paths_to_process = []
    
    if data_source in ["Upload Images", "Use Last Scan"]:
        if data_source == "Upload Images":
            uploaded_files = st.file_uploader("Upload images", accept_multiple_files=True, type=['jpg','png'])
            if uploaded_files:
                with tempfile.TemporaryDirectory() as temp_dir:
                    for f in uploaded_files:
                        path = os.path.join(temp_dir, f.name)
                        with open(path, "wb") as w: w.write(f.getbuffer())
                        image_paths_to_process.append(path)
                    
        elif data_source == "Use Last Scan":
            if scanner.current_scan_folder and os.path.exists(scanner.current_scan_folder):
                st.info(f"Using scan from: {scanner.current_scan_folder}")
                image_paths_to_process = [
                    os.path.join(scanner.current_scan_folder, f) 
                    for f in os.listdir(scanner.current_scan_folder) 
                    if f.lower().endswith(('.jpg', '.png'))
                ]
            else:
                st.warning("No recent scan found.")

        if image_paths_to_process:
            if st.button("✨ Reconstruct 3D Scene"):
                try:
                    from dust3r.image_pairs import make_pairs
                    from dust3r.utils.image import load_images
                    from dust3r.inference import inference
                    model, device = load_dust3r_model()
                    
                    if model:
                        with st.spinner("Processing..."):
                            images = load_images(image_paths_to_process, size=512)
                            pairs = make_pairs(images, scene_graph='complete', prefilter=None, symmetrize=True)
                            output = inference(pairs, model, device, batch_size=1)
                            
                            all_points = []
                            for key, res in output.items():
                                if res and 'pts3d' in res:
                                    pts = res['pts3d'].detach().cpu().numpy()
                                    valid_mask = pts.reshape(-1, 3).max(axis=1) < 100 
                                    all_points.append(pts.reshape(-1, 3)[valid_mask][::10])

                            if all_points:
                                final_points = np.concatenate(all_points, axis=0)
                                st.plotly_chart(visualize_point_cloud(final_points), use_container_width=True)
                                pcd = trimesh.points.PointCloud(final_points)
                                st.download_button("Download .PLY", pcd.export(file_type='ply'), "model.ply")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- OPTION C: LOAD EXISTING MODEL ---
    elif data_source == "Load Existing 3D Model":
        uploaded_model = st.file_uploader("Upload 3D Model", type=['stl', 'ply', 'obj', 'glb'])
        
        if uploaded_model:
            # 1. Create a temporary path
            suffix = f".{uploaded_model.name.split('.')[-1]}"
            # delete=False is required so we can close it and open it again with trimesh
            tmp_path = ""
            
            try:
                # Write the file and CLOSE it immediately
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_model.getbuffer())
                    tmp_path = tmp.name
                # File is now CLOSED here, safe to read/delete

                # 2. Process the file
                with st.spinner("Parsing 3D file..."):
                    mesh = trimesh.load(tmp_path)
                    points = None
                    colors = None
                    
                    if isinstance(mesh, trimesh.Scene):
                        if len(mesh.geometry) > 0:
                            points = np.concatenate([g.vertices for g in mesh.geometry.values()])
                    elif hasattr(mesh, 'vertices'):
                        points = mesh.vertices
                        # Try to get colors if available
                        if hasattr(mesh.visual, 'vertex_colors'):
                            c = mesh.visual.vertex_colors
                            if hasattr(c, 'ndim') and c.ndim == 2 and c.shape[1] >= 3:
                                colors = c[:, :3] / 255.0
                    
                    if points is not None:
                        st.success(f"Loaded {len(points)} points")
                        st.plotly_chart(visualize_point_cloud(points, colors), use_container_width=True)
                    else:
                        st.error("Could not extract vertices from this model.")
                        
            except Exception as e:
                st.error(f"Error loading file: {e}")
                
            finally:
                # 3. Clean up (The file is definitely closed now)
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except PermissionError:
                        # If Windows is still holding it, just pass to avoid crashing the app
                        pass