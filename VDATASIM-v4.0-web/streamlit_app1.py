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
    st.markdown("🟢 Data Drive (Online)")
    st.markdown("🔴 Drive Offline")
    st.markdown("🟣 Local Parity")
    st.markdown("🔵 Global Parity")
    st.markdown("🟡 Hot Spare")

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
    
    # Display drives using native Streamlit buttons
    st.markdown(f"### Dbox-{selected_dbox} Drive Grid")
    st.caption("Click on any drive to toggle its status (online/offline)")
    
    dbox = storage.dboxes[selected_dbox]
    
    # Create grid using columns (11 drives per row = 4 rows)
    rows = 4
    cols_per_row = 11
    
    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            drive_idx = row * cols_per_row + col_idx
            if drive_idx < len(dbox['all_drives']):
                drive_id = dbox['all_drives'][drive_idx]
                drive_type = storage.get_drive_type(drive_id)
                online = storage.drive_status[drive_id]
                preview = storage.drive_data_preview[drive_id]
                
                # Determine button type and emoji
                if not online:
                    button_type = "secondary"
                    emoji = "🔴"
                elif drive_type == "Local Parity":
                    button_type = "secondary"
                    emoji = "🟣"
                elif drive_type == "Global Parity":
                    button_type = "secondary"
                    emoji = "🔵"
                elif drive_type == "Hot Spare":
                    button_type = "secondary"
                    emoji = "🟡"
                else:
                    button_type = "primary" if online else "secondary"
                    emoji = "🟢"
                
                with cols[col_idx]:
                    button_label = f"{emoji}\n{drive_id}\n{preview[:4]}"
                    if st.button(
                        button_label,
                        key=f"drive_{drive_id}",
                        use_container_width=True,
                        type=button_type,
                        help=f"Drive {drive_id} - {drive_type}\nStatus: {'Online' if online else 'Offline'}\nData: {preview}"
                    ):
                        storage.drive_status[drive_id] = not storage.drive_status[drive_id]
                        st.rerun()
    
    # Drive info display
    st.markdown("---")
    st.subheader("📊 Drive Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    dbox_drives = dbox['all_drives']
    online_count = sum(1 for d in dbox_drives if storage.drive_status[d])
    offline_count = len(dbox_drives) - online_count
    
    data_drives = [d for d in dbox_drives if storage.get_drive_type(d) == "Data"]
    parity_drives = [d for d in dbox_drives if "Parity" in storage.get_drive_type(d)]
    
    with col1:
        st.metric("Online Drives", online_count)
    with col2:
        st.metric("Offline Drives", offline_count)
    with col3:
        st.metric("Data Drives", len(data_drives))
    with col4:
        st.metric("Parity Drives", len(parity_drives))
    
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
💡 <strong>Tip:</strong> Click any drive button to toggle its status. 
Use the sidebar to upload files and manage the system.
Built with Streamlit • Erasure Coding Demo
</div>
""", unsafe_allow_html=True)
