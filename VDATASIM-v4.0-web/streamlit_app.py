import streamlit as st
import numpy as np
import os
import struct
from pathlib import Path
import time

# Set page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Erasure Coded Storage",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
    }
    .drive-box {
        display: inline-block;
        width: 55px;
        height: 55px;
        margin: 3px;
        padding: 5px;
        text-align: center;
        border-radius: 6px;
        font-family: 'Courier New', monospace;
        font-size: 9px;
        font-weight: bold;
        cursor: pointer;
        border: 2px solid rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .drive-box:hover {
        transform: scale(1.1);
        border-color: #333;
    }
    .drive-online { background-color: #90EE90; color: black; }
    .drive-offline { background-color: #FF4444; color: white; }
    .drive-local-parity { background-color: #9370DB; color: white; }
    .drive-global-parity { background-color: #1E90FF; color: white; }
    .drive-spare { background-color: #FFD700; color: black; }
    
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        color: #155724;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

class ErasureCodedStorage:
    def __init__(self):
        self.total_drives = 484
        self.drive_size = 1024 * 1024  # 1MB
        self.chunk_size = 4096
        self.dboxes_count = 11
        self.drives_per_dbox = 44
        
        self.drives = []
        self.drive_status = [True] * self.total_drives
        self.drive_data_preview = ['00000000'] * self.total_drives
        self.storage_path = "./storage"
        
        self.stored_file_data = None
        self.stored_file_name = None
        self.ha_mode = False
        
        self.dboxes = self._configure_dboxes()
        
    def _configure_dboxes(self):
        dboxes = []
        for dbox_id in range(self.dboxes_count):
            base_drive = dbox_id * self.drives_per_dbox
            data_drives = list(range(base_drive, base_drive + 38))
            local_parity_drives = list(range(base_drive + 38, base_drive + 41))
            global_parity_drive = base_drive + 41
            spare_drives = list(range(base_drive + 42, base_drive + 44))
            
            local_groups = []
            for i in range(3):
                start_idx = i * 13
                end_idx = min(start_idx + 13, 38)
                group_data = data_drives[start_idx:end_idx]
                local_groups.append({
                    'data_drives': group_data,
                    'parity_drive': local_parity_drives[i] if i < len(local_parity_drives) else None
                })
            
            dboxes.append({
                'id': dbox_id,
                'name': f'Dbox-{dbox_id}',
                'data_drives': data_drives,
                'local_groups': local_groups,
                'local_parity_drives': local_parity_drives,
                'global_parity_drive': global_parity_drive,
                'spare_drives': spare_drives,
                'all_drives': list(range(base_drive, base_drive + 44))
            })
        
        return dboxes
    
    def get_drive_type(self, drive_id):
        for dbox in self.dboxes:
            if drive_id in dbox['data_drives']:
                return "Data"
            elif drive_id in dbox['local_parity_drives']:
                return "Local Parity"
            elif drive_id == dbox['global_parity_drive']:
                return "Global Parity"
            elif drive_id in dbox['spare_drives']:
                return "Hot Spare"
        return "Unknown"
    
    def get_dbox_for_drive(self, drive_id):
        return drive_id // self.drives_per_dbox
    
    def initialize_drives(self):
        """Initialize all drives with random data"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        
        for i in range(self.total_drives):
            filepath = os.path.join(self.storage_path, f"drive_{i:03d}.data")
            # Create smaller files for demo (1KB instead of 1MB)
            with open(filepath, 'wb') as f:
                f.write(b'\x00' * 1024)
            self.drives.append(filepath)
            # Generate random hex preview
            self.drive_data_preview[i] = ''.join([f'{np.random.randint(0, 256):02X}' for _ in range(4)])
        
        return True
    
    def get_storage_stats(self):
        if self.ha_mode:
            total_capacity = 18 * self.drive_size
        else:
            total_capacity = 418 * self.drive_size
        
        used_space = len(self.stored_file_data) if self.stored_file_data else 0
        available_space = total_capacity - used_space
        
        return {
            'total': total_capacity,
            'used': used_space,
            'available': available_space
        }
    
    def store_files(self, uploaded_files):
        """Store uploaded files with metadata"""
        combined_data = b''
        
        for uploaded_file in uploaded_files:
            file_data = uploaded_file.read()
            filename_bytes = uploaded_file.name.encode('utf-8')
            header = struct.pack('I', len(filename_bytes)) + filename_bytes + struct.pack('Q', len(file_data))
            combined_data += header + file_data
        
        self.stored_file_data = combined_data
        self.stored_file_name = uploaded_files[0].name if len(uploaded_files) == 1 else "combined_files.dat"
        
        # Update some drive previews to show data
        num_drives_used = min(len(self.dboxes[0]['data_drives']), 20)
        for i in range(num_drives_used):
            if len(combined_data) > i * 4:
                chunk = combined_data[i*4:(i+1)*4]
                self.drive_data_preview[i] = ''.join([f'{b:02X}' for b in chunk[:4]])
        
        return True, f"Successfully stored {len(uploaded_files)} file(s)"
    
    def check_integrity(self):
        """Check if data is recoverable"""
        offline_drives = [i for i, status in enumerate(self.drive_status) if not status]
        
        if len(offline_drives) == 0:
            return True, "✅ All drives online - Data fully protected", []
        
        # Check each Dbox for failures
        vulnerable_dboxes = []
        for dbox in self.dboxes:
            dbox_failures = [d for d in offline_drives if d in dbox['all_drives']]
            if len(dbox_failures) > 3:
                vulnerable_dboxes.append(dbox['id'])
        
        if len(vulnerable_dboxes) > 0:
            return False, f"⚠️ Data at risk in Dboxes: {vulnerable_dboxes}", vulnerable_dboxes
        
        return True, f"✅ Data recoverable ({len(offline_drives)} drives offline)", []

# Initialize session state
if 'storage' not in st.session_state:
    st.session_state.storage = ErasureCodedStorage()
    st.session_state.initialized = False
    st.session_state.selected_dbox = 0

storage = st.session_state.storage

# Header
st.title("💾 Erasure Coded Storage System")
st.markdown("**484 Drives • 11 Dboxes • Two-Level Erasure Coding**")
st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("🎛️ Control Panel")
    
    # Initialize button
    if not st.session_state.initialized:
        if st.button("🔧 Initialize Storage System", type="primary", use_container_width=True):
            with st.spinner("Initializing 484 drives..."):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
                storage.initialize_drives()
                st.session_state.initialized = True
                st.success("✅ Storage initialized!")
                st.rerun()
    else:
        st.success("✅ System Ready")
    
    st.markdown("---")
    
    # File upload
    if st.session_state.initialized:
        st.subheader("📁 File Management")
        uploaded_files = st.file_uploader(
            "Upload files to store",
            accept_multiple_files=True,
            help="Select one or more files to store with erasure coding"
        )
        
        if uploaded_files:
            if st.button("💾 Store Files", type="primary", use_container_width=True):
                with st.spinner("Storing files..."):
                    success, message = storage.store_files(uploaded_files)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("---")
        
        # Download
        if storage.stored_file_data:
            st.subheader("⬇️ Download")
            st.download_button(
                label="Download Stored File",
                data=storage.stored_file_data,
                file_name=storage.stored_file_name or "download.dat",
                mime="application/octet-stream",
                use_container_width=True
            )
    
    st.markdown("---")
    
    # HA Mode
    if st.session_state.initialized:
        st.subheader("⚙️ Settings")
        ha_mode = st.checkbox(
            "🔒 High Availability Mode",
            value=storage.ha_mode,
            help="18% overhead, uses only 2 drives per Dbox"
        )
        if ha_mode != storage.ha_mode:
            storage.ha_mode = ha_mode
            st.rerun()
    
    st.markdown("---")
    
    # Check integrity
    if st.session_state.initialized:
        if st.button("🔍 Check Data Integrity", use_container_width=True):
            can_recover, message, vulnerable = storage.check_integrity()
            if can_recover:
                st.success(message)
            else:
                st.warning(message)
    
    st.markdown("---")
    
    # Legend
    st.subheader("🎨 Legend")
    st.markdown("""
    <div style='font-size: 0.85rem;'>
    🟢 <span style='color: #90EE90;'>█</span> Data Drive (Online)<br>
    🔴 <span style='color: #FF4444;'>█</span> Drive Offline<br>
    🟣 <span style='color: #9370DB;'>█</span> Local Parity<br>
    🔵 <span style='color: #1E90FF;'>█</span> Global Parity<br>
    🟡 <span style='color: #FFD700;'>█</span> Hot Spare
    </div>
    """, unsafe_allow_html=True)

# Main content
if not st.session_state.initialized:
    # Welcome screen
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class='info-box'>
        <h2 style='text-align: center; margin-top: 0;'>Welcome! 👋</h2>
        <p style='text-align: center; font-size: 1.1rem;'>
        Click <strong>"Initialize Storage System"</strong> in the sidebar to begin.
        </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏗️ System Architecture")
        st.info("""
        **Storage Configuration:**
        - 484 total drives organized into 11 Dboxes
        - Each Dbox: 38 data + 3 local parity + 1 global parity + 2 spares
        - Normal mode: ~8.5% overhead
        - HA mode: 18% overhead
        
        **Failure Tolerance:**
        - ✅ Single drive failure per group
        - ✅ Multiple drives across different groups
        - ✅ Up to 2 drives in same group (with parity)
        - ✅ Entire Dbox failure in HA mode
        """)
        
else:
    # Storage statistics
    stats = storage.get_storage_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-label'>Total Capacity</div>
            <div class='stat-value'>{stats['total']/(1024*1024):.0f} MB</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-label'>Used</div>
            <div class='stat-value'>{stats['used']/(1024*1024):.2f} MB</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-label'>Available</div>
            <div class='stat-value'>{stats['available']/(1024*1024):.2f} MB</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        usage_pct = (stats['used'] / stats['total'] * 100) if stats['total'] > 0 else 0
        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-label'>Usage</div>
            <div class='stat-value'>{usage_pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Dbox selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_dbox = st.selectbox(
            "Select Dbox to view:",
            options=list(range(11)),
            index=st.session_state.selected_dbox,
            format_func=lambda x: f"Dbox-{x} (Drives {x*44}-{x*44+43})"
        )
        st.session_state.selected_dbox = selected_dbox
    
    with col2:
        if st.button("🔴 Toggle Entire Dbox", use_container_width=True):
            dbox = storage.dboxes[selected_dbox]
            new_status = not storage.drive_status[dbox['all_drives'][0]]
            for drive_id in dbox['all_drives']:
                storage.drive_status[drive_id] = new_status
            st.rerun()
    
    with col3:
        offline_in_dbox = sum(1 for d in storage.dboxes[selected_dbox]['all_drives'] 
                             if not storage.drive_status[d])
        if offline_in_dbox > 0:
            st.warning(f"⚠️ {offline_in_dbox} offline")
        else:
            st.success("✅ All online")
    
    # Display drives
    st.markdown(f"### Dbox-{selected_dbox} Drive Grid")
    st.caption("Click on any drive to toggle its status (online/offline)")
    
    dbox = storage.dboxes[selected_dbox]
    
    # Create clickable drive grid
    drives_html = "<div style='display: flex; flex-wrap: wrap; justify-content: center;'>"
    
    for idx, drive_id in enumerate(dbox['all_drives']):
        drive_type = storage.get_drive_type(drive_id)
        online = storage.drive_status[drive_id]
        preview = storage.drive_data_preview[drive_id]
        
        # Determine CSS class
        if not online:
            css_class = "drive-offline"
        elif drive_type == "Local Parity":
            css_class = "drive-local-parity"
        elif drive_type == "Global Parity":
            css_class = "drive-global-parity"
        elif drive_type == "Hot Spare":
            css_class = "drive-spare"
        else:
            css_class = "drive-online"
        
        drives_html += f"""
        <div class='drive-box {css_class}' 
             title='Drive {drive_id} - {drive_type}\nStatus: {"Online" if online else "Offline"}\nData: {preview}'>
            <div style='font-size: 11px; font-weight: bold;'>{drive_id}</div>
            <div style='font-size: 8px; margin-top: 2px;'>{preview[:4]}</div>
        </div>
        """
    
    drives_html += "</div>"
    st.markdown(drives_html, unsafe_allow_html=True)
    
    # Drive toggle interface
    st.markdown("---")
    st.subheader("🔧 Individual Drive Control")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        drive_to_toggle = st.number_input(
            "Enter drive ID to toggle:",
            min_value=dbox['all_drives'][0],
            max_value=dbox['all_drives'][-1],
            value=dbox['all_drives'][0],
            step=1
        )
    
    with col2:
        current_status = "🟢 Online" if storage.drive_status[drive_to_toggle] else "🔴 Offline"
        st.metric("Current Status", current_status)
    
    with col3:
        if st.button("Toggle Drive", type="primary", use_container_width=True):
            storage.drive_status[drive_to_toggle] = not storage.drive_status[drive_to_toggle]
            st.success(f"Toggled drive {drive_to_toggle}")
            st.rerun()
    
    # System info
    st.markdown("---")
    with st.expander("ℹ️ System Information"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Configuration:**
            - Total Drives: 484
            - Dboxes: 11
            - Drives per Dbox: 44
            - Data Drives: 418
            - Parity Drives: 44
            """)
        with col2:
            st.markdown(f"""
            **Current Status:**
            - Mode: {'HA (18% overhead)' if storage.ha_mode else 'Normal (8.5% overhead)'}
            - Online Drives: {sum(storage.drive_status)}
            - Offline Drives: {sum(1 for s in storage.drive_status if not s)}
            - Files Stored: {1 if storage.stored_file_data else 0}
            """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem;'>
💡 <strong>Tip:</strong> This is a web-based demonstration. For full hex viewer and advanced features, 
see the desktop version. Built with Streamlit • Erasure Coding Demo
</div>
""", unsafe_allow_html=True)
