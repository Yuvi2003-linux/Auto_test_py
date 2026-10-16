import time
import tkinter as tk
from tkinter import messagebox, ttk
import can
import cantools

class KillSwitchDemoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleOne - Kill Switch Automated Test Demo")
        self.root.geometry("520x480")
        self.root.resizable(False, False)

        # Initialize Hardware / DBC State
        self.bus = None
        self.db = None
        self.cmd_msg_def = None

        self._setup_can_bus()
        self._build_ui()

    def _setup_can_bus(self):
        """Loads the DBC file and connects to the PCAN USB channel."""
        try:
            # 1. Load the DBC database file
            self.db = cantools.database.load_file('SimpleOneGenX_02_12.dbc')
            self.cmd_msg_def = self.db.get_message_by_name('BCM_HMI_StatusCommands_23')

            # 2. Connect to PCAN Hardware on Windows (PEAK-System API)
            self.bus = can.Bus(
                interface='pcan',
                channel='PCAN_USBBUS1',
                bitrate=500000
            )
            self.conn_status = "Connected to PCAN_USBBUS1 (500 kbps)"
            self.conn_color = "#2e7d32"  # Dark green
        except Exception as e:
            self.bus = None
            self.conn_status = f"PCAN Connection Failed: {e}"
            self.conn_color = "#c62828"  # Dark red

    def _build_ui(self):
        """Constructs the GUI widgets."""
        # Header Title
        title_label = tk.Label(
            self.root, 
            text="Electric Vehicle Kill Switch Test Panel", 
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(15, 5))

        # Hardware Status Banner
        status_label = tk.Label(
            self.root, 
            text=self.conn_status, 
            fg=self.conn_color, 
            font=("Segoe UI", 9, "italic")
        )
        status_label.pack(pady=(0, 15))

        # Action Buttons Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(px=20, fill="x", pady=5)

        # Primary Kill Switch Test Button
        self.btn_kill_switch = tk.Button(
            btn_frame,
            text="⚡ Run Kill Switch Test Sequence",
            command=self.run_kill_switch_test,
            font=("Segoe UI", 11, "bold"),
            bg="#0288d1",
            fg="white",
            activebackground="#01579b",
            activeforeground="white",
            height=2,
            cursor="hand2"
        )
        self.btn_kill_switch.pack(fill="x", pady=5)

        # Full Sequence Test Button
        self.btn_full_seq = tk.Button(
            btn_frame,
            text="🔄 Run Full Ignition & Kill Switch Test Cycle",
            command=self.run_full_cycle_test,
            font=("Segoe UI", 10),
            bg="#eceff1",
            fg="#37474f",
            height=2,
            cursor="hand2"
        )
        self.btn_full_seq.pack(fill="x", pady=5)

        # Activity / Execution Log Area
        log_frame = tk.LabelFrame(self.root, text=" Test Execution Log ", font=("Segoe UI", 10, "bold"), px=10, py=10)
        log_frame.pack(px=20, pady=15, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), bg="#f5f5f5")
        self.log_text.pack(fill="both", expand=True)

        self.log("GUI Initialized successfully.")
        if not self.bus:
            self.log("WARNING: PCAN device not detected. Connect PCAN USB and restart script.")

    def log(self, text):
        """Helper to output timestamps and log messages to the UI text box."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_text.see(tk.END)
        self.root.update()

    def send_bcm_command(self, key_on=0, kill_switch=0, duration_sec=1.5):
        """
        Encodes and transmits BCM_HMI_StatusCommands_23 cyclically for a duration.
        """
        if not self.bus:
            messagebox.showerror("Error", "PCAN Hardware is not connected!")
            return False

        # Construct dictionary for all signals (filling unused signals with 0)
        signals = {
            'BCM_H_KeyOnoff_Command': key_on,
            'BCM_Sw_KIllSwitch_Status': kill_switch,
            'BCM_Sw_Ignition_Status': 0, 'BCM_Sw_Standsensor_status': 0,
            'BCM_Sw_Park_Status': 0, 'BCM_Sw_Leftbrake_status': 0,
            'BCM_Sw_Rightbrake_Status': 0, 'BCM_Sw_Horn_Status': 0,
            'BCM_Sw_Bootspace_Status': 0, 'BCM_Sw_HighBeam_status': 0,
            'BCM_Sw_Leftindicator_status': 0, 'BCM_Sw_Rightindicator_status': 0,
            'BCM_L_Leftindicator_status': 0, 'BCM_L_RightIndicator_Status': 0,
            'BCM_L_HighBeam_Status': 0, 'BCM_L_Hazard_Status': 0,
            'Portable_battery_conn_Status': 0, 'Portable_battery_lock_Status': 0,
            'BCM_H_CallAccept_Command': 0, 'BCM_H_CallReject_Command': 0,
            'BCM_H_PlayPause_Command': 0, 'BCM_H_EnableTouch_Command': 0,
            'BCM_H_SOMPower_Command': 0, 'BCM_Sw_Midindicator_Status': 0,
            'BCM_Sw_ChargerFeedback': 0, 'BCM_H_music_track_next_Command': 0,
            'BCM_H_music_track_previous_Cmd': 0, 'BCM_H_music_volume_up_Command': 0,
            'BCM_H_music_volume_down_Command': 0, 'BCM_H_VIN_check_Command': 0,
            'BCM_H_VIN_verify_done': 0, 'BCM_Drop_Safe_Action': 0,
            'BCM_SliderRange': 0, 'BCM_Welcome_Light_ACK': 0,
            'BCM_Escort_Light_ACK': 0, 'BCM_Drop_Safe_ACK': 0,
            'brake_status': 0, 'BCM_Theft_Status': 0,
            'BCM_Sw_ModeRight_Status': 0, 'BCM_Sw_ModeLeft_Status': 0,
            'BCM_Sw_Hazard_Status': 0, 'BCM_Tow_Status': 0,
            'TD_SwitchtoEco': 0, 'Batt_to_switch': 0,
            'BCM_Sw_NavigationMiddle_Status': 0, 'BCM_Sw_NavigationLeft_Status': 0,
            'BCM_Sw_NavigationRight_Status': 0, 'BCM_Sw_NavigationTop_Status': 0,
            'BCM_Sw_NavigationBottom_Status': 0
        }

        # Encode signal dictionary to raw payload bytes using DBC rules
        payload_bytes = self.cmd_msg_def.encode(signals)

        # Build 29-bit Extended CAN Message
        frame = can.Message(
            arbitration_id=self.cmd_msg_def.frame_id,
            data=payload_bytes,
            is_extended_id=self.cmd_msg_def.is_extended_frame
        )

        # Transmit frame cyclically at 50ms intervals
        cycles = int(duration_sec / 0.05)
        for _ in range(cycles):
            self.bus.send(frame)
            time.sleep(0.05)
        return True

    def run_kill_switch_test(self):
        """Executes the specific Kill Switch toggle test case."""
        self.btn_kill_switch.config(state="disabled")
        self.log("▶ TEST STARTED: Kill Switch Toggle Test")

        # Step A: Engage Kill Switch (Key ON = 1, Kill Switch = 1)
        self.log("[TX] Transmitting: Key ON (1) & Kill Switch ACTIVE (1)...")
        if self.send_bcm_command(key_on=1, kill_switch=1, duration_sec=2.0):
            self.log("--> Kill Switch ACTIVE command sent for 2 seconds.")

            # Step B: Release Kill Switch (Key ON = 1, Kill Switch = 0)
            self.log("[TX] Transmitting: Key ON (1) & Kill Switch INACTIVE (0)...")
            self.send_bcm_command(key_on=1, kill_switch=0, duration_sec=2.0)
            self.log("--> Kill Switch INACTIVE command sent for 2 seconds.")

            self.log("✅ TEST PASSED: Kill Switch Toggle Sequence Completed.\n")
            messagebox.showinfo("Test Complete", "Kill Switch Test Sequence Completed Successfully!")

        self.btn_kill_switch.config(state="normal")

    def run_full_cycle_test(self):
        """Executes a full HMI ON -> Kill Switch Active -> Kill Switch Inactive -> HMI OFF cycle."""
        self.btn_full_seq.config(state="disabled")
        self.log("▶ TEST STARTED: Full Ignition & Kill Switch Test Sequence")

        # Step 1: Turn HMI ON
        self.log("Step 1: Turning HMI ON (Key ON = 1)...")
        if self.send_bcm_command(key_on=1, kill_switch=0, duration_sec=2.0):
            
            # Step 2: Activate Kill Switch
            self.log("Step 2: Activating Kill Switch (Kill Switch = 1)...")
            self.send_bcm_command(key_on=1, kill_switch=1, duration_sec=2.0)

            # Step 3: Deactivate Kill Switch
            self.log("Step 3: Deactivating Kill Switch (Kill Switch = 0)...")
            self.send_bcm_command(key_on=1, kill_switch=0, duration_sec=2.0)

            # Step 4: Turn HMI OFF
            self.log("Step 4: Turning HMI OFF (Key ON = 0)...")
            self.send_bcm_command(key_on=0, kill_switch=0, duration_sec=2.0)

            self.log("✅ TEST PASSED: Full Sequence Finished Successfully.\n")
            messagebox.showinfo("Sequence Complete", "Full Automated Sequence Completed Successfully!")

        self.btn_full_seq.config(state="normal")

    def __del__(self):
        """Release CAN channel on window close."""
        if self.bus:
            self.bus.shutdown()

if __name__ == "__main__":
    root = tk.Tk()
    app = KillSwitchDemoGUI(root)
    root.mainloop()
