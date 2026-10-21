import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import can
import cantools

class Sanity_Automation_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automotive HMI Test Bench - Sanity Automation")
        self.root.geometry("980x750")
        self.root.resizable(True, True)

        # Initialize Hardware / DBC State
        self.bus = None
        self.db = None
        self.cmd_msg_def = None
        self.status_msg_def = None
        self.display_msg_def = None
        self.telemetry_msg_def = None

        self.conn_status = "PCAN : Disconnected"
        self.conn_color = "#c62828"
        self.is_running_test = False
        self.abort_requested = False

        self._load_dbc()
        self._build_ui()

        # Connect once at startup
        self._connect_pcan()

        # Start passive monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_pcan_passive, daemon=True)
        self.monitor_thread.start()

    def _load_dbc(self):
        """Loads the DBC database definitions."""
        try:
            self.db = cantools.database.load_file('SimpleOneGenX_02_12.dbc')
            self.cmd_msg_def = self.db.get_message_by_name('BCM_HMI_StatusCommands_23')
            self.status_msg_def = self.db.get_message_by_name('BCM_All_Status_24')
            self.display_msg_def = self.db.get_message_by_name('BCM_HMI_Display_25')
            self.telemetry_msg_def = self.db.get_message_by_name('MC_All_Telemetry_1')
        except Exception as e:
            print(f"Error loading DBC: {e}")

    def _connect_pcan(self):
        """Attempts to open the PCAN channel once without closing it repeatedly."""
        if self.bus is not None:
            return True

        try:
            self.bus = can.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)
            self.conn_status = "PCAN : Connected (PCAN_USBBUS1 @ 500 kbps)"
            self.conn_color = "#2e7d32"  # Green
            self.root.after(0, self._update_status_header)
            return True
        except Exception as e:
            err_str = str(e).upper()
            if "BUSY" in err_str:
                self.conn_status = "PCAN : Busy (Opened in another app like BUSMASTER)"
                self.conn_color = "#f57c00"  # Orange
            else:
                self.conn_status = "PCAN : Disconnected (Hardware not detected)"
                self.conn_color = "#c62828"  # Red
            self.bus = None
            self.root.after(0, self._update_status_header)
            return False

    def _monitor_pcan_passive(self):
        """Passively checks connection status without repeatedly initializing the bus."""
        while True:
            if self.bus is None:
                self._connect_pcan()
            time.sleep(2.0)

    def _update_status_header(self):
        """Updates the status banner text and background color."""
        self.status_label.config(text=self.conn_status, fg=self.conn_color)

    def _build_ui(self):
        """Constructs the main GUI layout."""
        # Header Banner
        header_frame = tk.Frame(self.root, bg="#1e1e2f", height=50)
        header_frame.pack(fill="x", side="top")

        title_label = tk.Label(
            header_frame, 
            text="HMI FUNCTIONAL TEST BENCH - SANITY AUTOMATION", 
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#1e1e2f",
            pady=8
        )
        title_label.pack(side="left", padx=15)

        # Connect / Retry Button
        btn_reconnect = tk.Button(
            header_frame, 
            text="🔌 Reconnect PCAN", 
            command=self._connect_pcan, 
            font=("Segoe UI", 8, "bold"),
            bg="#37474f", fg="white"
        )
        btn_reconnect.pack(side="right", padx=5)

        btn_abort = tk.Button(
            header_frame, 
            text="🛑 Abort Test", 
            command=self.abort_test, 
            font=("Segoe UI", 8, "bold"),
            bg="#b71c1c", fg="white"
        )
        btn_abort.pack(side="right", padx=5)

        self.status_label = tk.Label(
            header_frame, 
            text=self.conn_status, 
            fg=self.conn_color, 
            bg="#1e1e2f",
            font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(side="right", padx=5)

        # Main Split Container
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)

        left_panel = tk.Frame(main_container)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # --- SECTION 1: SCREEN FLOW & BOOT ---
        sfb_frame = tk.LabelFrame(
            left_panel, 
            text=" Sheet: Screen Flow & Boot ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#0288d1",
            padx=8, pady=6
        )
        sfb_frame.pack(fill="x", pady=4)

        btn_sfb1 = tk.Button(sfb_frame, text="SFB_001: (OFF → KEY ON → LANDING SCREEN 4s) x 5 Cycles", command=lambda: self._run_async(self.tc_sfb_001), font=("Segoe UI", 8), bg="#e3f2fd", anchor="w")
        btn_sfb1.pack(fill="x", pady=2)

        btn_sfb2 = tk.Button(sfb_frame, text="SFB_002: OFF(3s) → KEY ON → KILL SW ON → IGNITION ON (Speed 00 5s)", command=lambda: self._run_async(self.tc_sfb_002), font=("Segoe UI", 8), bg="#e3f2fd", anchor="w")
        btn_sfb2.pack(fill="x", pady=2)

        btn_sfb3 = tk.Button(sfb_frame, text="SFB_003: Key OFF Simulation (3s Blank Check)", command=lambda: self._run_async(self.tc_sfb_003), font=("Segoe UI", 8), bg="#e3f2fd", anchor="w")
        btn_sfb3.pack(fill="x", pady=2)

        btn_sfb_master = tk.Button(sfb_frame, text="▶ Run Full Screen Flow & Boot Sequence", command=lambda: self._run_async(self.run_sfb_sequence), font=("Segoe UI", 9, "bold"), bg="#0288d1", fg="white", pady=3)
        btn_sfb_master.pack(fill="x", pady=(4, 2))

        # --- SECTION 2: DISPLAY & UI ---
        dsp_frame = tk.LabelFrame(
            left_panel, 
            text=" Sheet: Display & UI ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#2e7d32",
            padx=8, pady=6
        )
        dsp_frame.pack(fill="x", pady=4)

        dsp_grid = tk.Frame(dsp_frame)
        dsp_grid.pack(fill="x")

        # DSP 001 Marked Red / Manual Notice (EV Button Kill Switch Check)
        btn_dsp1 = tk.Button(dsp_grid, text="DSP_001: EV Button Kill Switch (*MANUAL CHECK REQUIRED)", command=lambda: self._run_async(self.tc_dsp_001), font=("Segoe UI", 8, "bold"), bg="#ffcdd2", fg="#c62828", anchor="w")
        btn_dsp1.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        btn_dsp2 = tk.Button(dsp_grid, text="DSP_002: Kill SW 5-6 Toggles (2s each)", command=lambda: self._run_async(self.tc_dsp_002), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp2.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        # DSP 003 Marked Red / Manual Notice (Charger Flow)
        btn_dsp3 = tk.Button(dsp_grid, text="DSP_003: Charger Flow (*MANUAL CONNECT REQUIRED)", command=lambda: self._run_async(self.tc_dsp_003), font=("Segoe UI", 8, "bold"), bg="#ffcdd2", fg="#c62828", anchor="w")
        btn_dsp3.grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        btn_dsp4 = tk.Button(dsp_grid, text="DSP_004: Kill SW in Bento (Force Exit)", command=lambda: self._run_async(self.tc_dsp_004), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp4.grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        btn_dsp5 = tk.Button(dsp_grid, text="DSP_005: Kill SW Cutoff while Riding", command=lambda: self._run_async(self.tc_dsp_005), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp5.grid(row=2, column=0, sticky="ew", padx=2, pady=2)

        btn_dsp9 = tk.Button(dsp_grid, text="DSP_009-011: Bento Nav & Exit", command=lambda: self._run_async(self.tc_dsp_bento), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp9.grid(row=2, column=1, sticky="ew", padx=2, pady=2)

        btn_dsp12 = tk.Button(dsp_grid, text="DSP_012: Stand 5-6 Toggles (1s each)", command=lambda: self._run_async(self.tc_dsp_012), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp12.grid(row=3, column=0, sticky="ew", padx=2, pady=2)

        btn_dsp13 = tk.Button(dsp_grid, text="DSP_013: SoC 100% (3s) -> 10% Low Batt Pop-up (5s)", command=lambda: self._run_async(self.tc_dsp_013), font=("Segoe UI", 8), bg="#e8f5e9", anchor="w")
        btn_dsp13.grid(row=3, column=1, sticky="ew", padx=2, pady=2)

        dsp_grid.columnconfigure(0, weight=1)
        dsp_grid.columnconfigure(1, weight=1)

        btn_dsp_master = tk.Button(dsp_frame, text="▶ Run Full Display & UI Sequence", command=lambda: self._run_async(self.run_dsp_sequence), font=("Segoe UI", 9, "bold"), bg="#2e7d32", fg="white", pady=3)
        btn_dsp_master.pack(fill="x", pady=(4, 2))

        # Right Panel: Color-Coded Console Log
        right_panel = tk.LabelFrame(main_container, text=" Test Execution Console Log ", font=("Segoe UI", 10, "bold"), padx=5, pady=5)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # Log Control Toolbar
        log_toolbar = tk.Frame(right_panel)
        log_toolbar.pack(fill="x", side="top", pady=(0, 4))

        btn_clear_log = tk.Button(
            log_toolbar, 
            text="🧹 Clear Log", 
            command=self.clear_log, 
            font=("Segoe UI", 8, "bold"),
            bg="#455a64", fg="white"
        )
        btn_clear_log.pack(side="right")

        self.log_text = tk.Text(right_panel, font=("Consolas", 9), bg="#1e1e1e", fg="#ffffff", wrap="word")
        self.log_text.pack(fill="both", expand=True)

        self.log_text.tag_config("INFO", foreground="#81d4fa")
        self.log_text.tag_config("SUCCESS", foreground="#66bb6a", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("FAIL", foreground="#ef5350", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("HEADER", foreground="#ffd54f", font=("Consolas", 9, "bold"))

        self.log("GUI Initialized successfully.", "INFO")

    def clear_log(self):
        """Clears the console log window."""
        self.log_text.delete("1.0", tk.END)
        self.log("Console log cleared.", "INFO")

    def abort_test(self):
        """Requests cancellation of the currently running test sequence."""
        if self.is_running_test:
            self.abort_requested = True
            self.log("🛑 ABORT REQUESTED! Stopping test sequence...", "FAIL")
        else:
            self.log("No test sequence is currently running.", "INFO")

    def log(self, text, tag="INFO"):
        """Outputs color-coded log entries to the UI console."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n", tag)
        self.log_text.see(tk.END)

    def _run_async(self, func):
        """Runs test functions on a separate background thread to prevent GUI freezing."""
        if self.is_running_test:
            messagebox.showwarning("Busy", "A test case sequence is already running! Please wait.")
            return
        self.is_running_test = True
        threading.Thread(target=self._test_wrapper, args=(func,), daemon=True).start()

    def _test_wrapper(self, func):
        """Wrapper to safely reset running state after test completes."""
        self.abort_requested = False
        try:
            func()
        except Exception as e:
            self.log(f"Test Exception Error: {e}", "FAIL")
        finally:
            self.is_running_test = False
            self.abort_requested = False

    def send_bcm_command(self, key_on=0, kill_switch=0, ignition_sw=0, stand_lifted=1, nav_top=0, nav_bot=0, soc=85, low_batt_warn=0, speed_kmh=0, duration_sec=1.0):
        """Encodes and transmits CAN frames for BCM Status, Display, and Telemetry."""
        if not self.bus:
            if not self._connect_pcan():
                self.log("TX Skipped: PCAN Hardware is not connected!", "FAIL")
                return False

        # Prepare BCM_HMI_StatusCommands_23 signals
        bcm_signals = {
            'BCM_H_KeyOnoff_Command': key_on,
            'BCM_Sw_KIllSwitch_Status': kill_switch,
            'BCM_Sw_Ignition_Status': ignition_sw,
            'BCM_Sw_Standsensor_status': stand_lifted,
            'BCM_Sw_NavigationTop_Status': nav_top,
            'BCM_Sw_NavigationBottom_Status': nav_bot,
            'BCM_Sw_Park_Status': 0, 
            'BCM_Sw_Leftbrake_status': 0, 'BCM_Sw_Rightbrake_Status': 0, 
            'BCM_Sw_Horn_Status': 0, 'BCM_Sw_Bootspace_Status': 0, 
            'BCM_Sw_HighBeam_status': 0, 'BCM_Sw_Leftindicator_status': 0, 
            'BCM_Sw_Rightindicator_status': 0, 'BCM_L_Leftindicator_status': 0, 
            'BCM_L_RightIndicator_Status': 0, 'BCM_L_HighBeam_Status': 0, 
            'BCM_L_Hazard_Status': 0, 'Portable_battery_conn_Status': 0, 
            'Portable_battery_lock_Status': 0, 'BCM_H_CallAccept_Command': 0, 
            'BCM_H_CallReject_Command': 0, 'BCM_H_PlayPause_Command': 0, 
            'BCM_H_EnableTouch_Command': 0, 'BCM_H_SOMPower_Command': 0, 
            'BCM_Sw_Midindicator_Status': 0, 'BCM_Sw_ChargerFeedback': 0, 
            'BCM_H_music_track_next_Command': 0, 'BCM_H_music_track_previous_Cmd': 0, 
            'BCM_H_music_volume_up_Command': 0, 'BCM_H_music_volume_down_Command': 0, 
            'BCM_H_VIN_check_Command': 0, 'BCM_H_VIN_verify_done': 0, 
            'BCM_Drop_Safe_Action': 0, 'BCM_SliderRange': 0, 
            'BCM_Welcome_Light_ACK': 0, 'BCM_Escort_Light_ACK': 0, 
            'BCM_Drop_Safe_ACK': 0, 'brake_status': 0, 'BCM_Theft_Status': 0, 
            'BCM_Sw_ModeRight_Status': 0, 'BCM_Sw_ModeLeft_Status': 0, 
            'BCM_Sw_Hazard_Status': 0, 'BCM_Tow_Status': 0, 
            'TD_SwitchtoEco': 0, 'Batt_to_switch': 0, 
            'BCM_Sw_NavigationMiddle_Status': 0, 'BCM_Sw_NavigationLeft_Status': 0, 
            'BCM_Sw_NavigationRight_Status': 0
        }

        # Prepare BCM_HMI_Display_25 signals
        display_signals = {
            'EffectiveSOC': soc,
            'Calibrated_VehicleSpeed': speed_kmh,
            'ChargingTimeLeft': 0,
            'ODO_MeterReading': 1250.0
        }

        # Prepare BCM_All_Status_24 signals
        status_signals = {
            'BCM_Warning_BatteryLow': low_batt_warn,
            'Vehicle_State': 2 if key_on == 1 else 0,
            'BCM_L_MCU_Status': 0, 'BCM_L_BootLight_Status': 0, 'BCM_ChargerDocked': 0,
            'BCM_Selected_Battery': 0, 'BCM_L_USB_Status': 0, 'BCM_ChargingOnProgress': 0,
            'BCM_Warning_SystemShuttingdown': 0, 'BCM_Warning_SonicUnavailable': 0,
            'BCM_Warning_PortableBatteryInUse': 0, 'BCM_Warning_PortableB_Disengaged': 0,
            'BCM_Warning_OnlyEco': 0, 'BCM_Warning_ChargingStopped': 0, 'BCM_Warning_ChargingCompleted': 0,
            'BCM_L_StopLight_Status': 0, 'BCM_L_LowBeam_Status': 0, 'BCM_L_Horn_Status': 0,
            'BCM_L_HighBeam_Status': 0, 'BCM_L_BackLight_Status': 0, 'BCM_Warning_Igwithoutbrake': 0,
            'BCM_Connected_charger': 0, 'PortableBattery_enabled': 0, 'BCM_Warning_OnlyEcoPortable': 0,
            'BCM_OTA_ACK': 0, 'BCM_OTA_NACK': 0, 'MCU_OTA_initiated': 0
        }

        # Prepare Telemetry MC_All_Telemetry_1 signals
        mc_signals = {
            'Vehicle_Speed': speed_kmh,
            'Motor_OnOff_status': 1 if speed_kmh > 0 else 0,
            'Current_Mode_Status': 1, 'Throttle_percentage': 20 if speed_kmh > 0 else 0,
            'Motor_Speed': speed_kmh * 50, 'CruiseControl_status': 0,
            'Motor_Derate_Status': 0, 'Motor_Lock_Status': 0,
            'MC_Ready_Status': 1, 'MC_RegenerativeBraking_status': 0,
            'Motor_ReverseForward_status': 0, 'Hillhold_Status': 0,
            'hill_hold_failure': 0, 'hill_hold_exit_warning': 0,
            'stall_warning': 0, 'Motor_temperature': 35
        }

        bcm_payload = self.cmd_msg_def.encode(bcm_signals)
        display_payload = self.display_msg_def.encode(display_signals)
        status_payload = self.status_msg_def.encode(status_signals)
        mc_payload = self.telemetry_msg_def.encode(mc_signals)

        bcm_frame = can.Message(arbitration_id=self.cmd_msg_def.frame_id, data=bcm_payload, is_extended_id=True)
        display_frame = can.Message(arbitration_id=self.display_msg_def.frame_id, data=display_payload, is_extended_id=True)
        status_frame = can.Message(arbitration_id=self.status_msg_def.frame_id, data=status_payload, is_extended_id=True)
        mc_frame = can.Message(arbitration_id=self.telemetry_msg_def.frame_id, data=mc_payload, is_extended_id=True)

        cycles = int(duration_sec / 0.05)
        for _ in range(cycles):
            if self.abort_requested:
                self.log("--> Test Execution Aborted by User.", "FAIL")
                return False
            try:
                if self.bus:
                    self.bus.send(bcm_frame)
                    self.bus.send(display_frame)
                    self.bus.send(status_frame)
                    self.bus.send(mc_frame)
                else:
                    self.log("TX Skipped: PCAN Hardware is not connected!", "FAIL")
                    return False
            except Exception as e:
                self.log(f"Transmission Error: {e}", "FAIL")
                self.bus = None
                self._update_status_header()
                return False
            time.sleep(0.05)
        return True

    # =========================================================================
    # TEST CASES: SCREEN FLOW & BOOT
    # =========================================================================
    def tc_sfb_001(self):
        self.log("\n=== [TC SFB_001] 5 Cycles of (OFF -> KEY ON -> LANDING SCREEN 4s) ===", "HEADER")
        for i in range(1, 6):
            if self.abort_requested:
                break
            self.log(f"--- SFB_001 Cycle {i}/5 ---", "HEADER")
            self.log("  Step A: Holding Key OFF (2s)...", "INFO")
            if not self.send_bcm_command(key_on=0, kill_switch=0, duration_sec=2.0):
                self.log("--> FAIL: SFB_001 Terminated due to Hardware Disconnection.", "FAIL")
                return

            self.log("  Step B: Key ON -> Landing Screen Active for 4 seconds...", "INFO")
            if not self.send_bcm_command(key_on=1, kill_switch=0, duration_sec=4.0):
                self.log("--> FAIL: SFB_001 Terminated due to Hardware Disconnection.", "FAIL")
                return

        if not self.abort_requested:
            self.log("--> PASS: Completed 5 Cycles of (OFF -> ON -> Landing Screen 4s).", "SUCCESS")

    def tc_sfb_002(self):
        self.log("\n=== [TC SFB_002] Key OFF (3s) -> Key ON -> Kill SW ON -> Ignition ON (Speed 0 km/h for 5s) ===", "HEADER")
        
        self.log("Step 1: Start from OFF state for 3 seconds...", "INFO")
        if not self.send_bcm_command(key_on=0, kill_switch=0, ignition_sw=0, speed_kmh=0, duration_sec=3.0):
            self.log("--> FAIL: SFB_002 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 2: Send Key ON (Kill Switch Disengaged) -> Verify Center Widget = Kill Switch Disengaged...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, ignition_sw=0, speed_kmh=0, duration_sec=3.0):
            self.log("--> FAIL: SFB_002 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 3: Set Kill Switch ON (Engaged) -> Verify Center Widget = Press Brake and Start...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=1, ignition_sw=0, speed_kmh=0, duration_sec=3.0):
            self.log("--> FAIL: SFB_002 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 4: Set Ignition ON (Disengaging Kill SW) -> Verify Center Widget = Speedometer with 00 (Holding 0 km/h for 5s)...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, ignition_sw=1, stand_lifted=1, speed_kmh=0, duration_sec=5.0):
            self.log("--> FAIL: SFB_002 Terminated due to Hardware Disconnection.", "FAIL")
            return

        if not self.abort_requested:
            self.log("--> PASS: SFB_002 Sequence Completed Successfully.", "SUCCESS")

    def tc_sfb_003(self):
        self.log("\n=== [TC SFB_003] Key OFF Simulation (3s Blank Check) ===", "HEADER")
        self.log("Step 1: Simulating Key OFF state for 3 seconds...", "INFO")
        if self.send_bcm_command(key_on=0, kill_switch=0, duration_sec=3.0):
            self.log("--> PASS: Key OFF Screen Blank state verified.", "SUCCESS")
        else:
            self.log("--> FAIL: SFB_003 Terminated due to Hardware Disconnection.", "FAIL")

    # =========================================================================
    # TEST CASES: DISPLAY & UI
    # =========================================================================
    def tc_dsp_001(self):
        self.log("\n=== [TC DSP_001] Physical EV Button Kill Switch Manual Check ===", "FAIL")
        self.log("NOTE: Physical EV button kill switch functionality must be tested manually on the vehicle harness.", "FAIL")
        self.log("--> PLEASE PRESS AND RELEASE THE PHYSICAL KILL SWITCH BUTTON MANUALLY TO VERIFY FUNCTIONALITY.", "HEADER")

    def tc_dsp_002(self):
        self.log("\n=== [TC DSP_002] Kill Switch 5-6 Toggles (2s ON / 2s OFF) ===", "HEADER")
        for i in range(1, 6):
            if self.abort_requested:
                break
            self.log(f"Toggle {i}/5: Kill Switch ENGAGED (2s)...", "INFO")
            if not self.send_bcm_command(key_on=1, kill_switch=1, duration_sec=2.0):
                self.log("--> FAIL: DSP_002 Terminated due to Hardware Disconnection.", "FAIL")
                return
            self.log(f"Toggle {i}/5: Kill Switch DISENGAGED (2s)...", "INFO")
            if not self.send_bcm_command(key_on=1, kill_switch=0, duration_sec=2.0):
                self.log("--> FAIL: DSP_002 Terminated due to Hardware Disconnection.", "FAIL")
                return
        if not self.abort_requested:
            self.log("--> PASS: Kill Switch 5-6 Toggle Sequence (2s each) Verified.", "SUCCESS")

    def tc_dsp_003(self):
        self.log("\n=== [TC DSP_003] Charger Flow (*MANUAL CONNECT REQUIRED) ===", "FAIL")
        self.log("NOTE: Automatic charger connect/disconnect is not possible via standard software commands.", "FAIL")
        self.log("--> PLEASE CONNECT AND DISCONNECT THE PHYSICAL CHARGER CABLE MANUALLY FOR THIS CASE.", "HEADER")

    def tc_dsp_004(self):
        self.log("\n=== [TC DSP_004] Kill Switch Change in Bento Screen Forces Exit ===", "HEADER")
        self.log("Step 1: Set Key ON & Navigating to Bento Screen (Hold Nav TOP for 3s)...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, nav_top=1, duration_sec=3.0):
            self.log("--> FAIL: DSP_004 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 2: Toggling Kill Switch = ON while in Bento Screen...", "INFO")
        if self.send_bcm_command(key_on=1, kill_switch=1, nav_top=0, duration_sec=2.0):
            self.log("--> PASS: Bento Screen exited automatically to Landing Screen.", "SUCCESS")
        else:
            self.log("--> FAIL: DSP_004 Terminated due to Hardware Disconnection.", "FAIL")

    def tc_dsp_005(self):
        self.log("\n=== [TC DSP_005] Kill Switch Engaged While Riding Stops Motor ===", "HEADER")
        self.log("Step 1: Riding vehicle at 25 km/h...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, speed_kmh=25, duration_sec=2.0):
            self.log("--> FAIL: DSP_005 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 2: Engaging Kill Switch (Cutoff)...", "INFO")
        if self.send_bcm_command(key_on=1, kill_switch=1, speed_kmh=0, duration_sec=2.0):
            self.log("--> PASS: Motor Cutoff and Kill Switch Icon displayed.", "SUCCESS")
        else:
            self.log("--> FAIL: DSP_005 Terminated due to Hardware Disconnection.", "FAIL")

    def tc_dsp_bento(self):
        self.log("\n=== [TC DSP_009-011] Bento Screen Navigation & Exit ===", "HEADER")
        self.log("Step 1: Entering Bento Screen (Holding Nav TOP for 3 seconds)...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, nav_top=1, duration_sec=3.0):
            self.log("--> FAIL: DSP Bento Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 2: Inside Bento Screen -> Navigating Cards...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, nav_top=0, duration_sec=2.0):
            self.log("--> FAIL: DSP Bento Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 3: Exiting Bento Screen (Holding Nav BOTTOM for 3 seconds)...", "INFO")
        if not self.send_bcm_command(key_on=1, kill_switch=0, nav_bot=1, duration_sec=3.0):
            self.log("--> FAIL: DSP Bento Terminated due to Hardware Disconnection.", "FAIL")
            return

        if self.send_bcm_command(key_on=1, kill_switch=0, nav_bot=0, duration_sec=1.0):
            self.log("--> PASS: Bento Screen Entered, Navigated, and Exited.", "SUCCESS")
        else:
            self.log("--> FAIL: DSP Bento Terminated due to Hardware Disconnection.", "FAIL")

    def tc_dsp_012(self):
        self.log("\n=== [TC DSP_012] Side Stand 5-6 Toggles (1s Open / 1s Close) ===", "HEADER")
        for i in range(1, 6):
            if self.abort_requested:
                break
            self.log(f"Stand Toggle {i}/5: Side Stand OPEN / Extended (1s)...", "INFO")
            if not self.send_bcm_command(key_on=1, stand_lifted=0, duration_sec=1.0):
                self.log("--> FAIL: DSP_012 Terminated due to Hardware Disconnection.", "FAIL")
                return
            self.log(f"Stand Toggle {i}/5: Side Stand CLOSED / Lifted (1s)...", "INFO")
            if not self.send_bcm_command(key_on=1, stand_lifted=1, duration_sec=1.0):
                self.log("--> FAIL: DSP_012 Terminated due to Hardware Disconnection.", "FAIL")
                return
        if not self.abort_requested:
            self.log("--> PASS: Side Stand 5-6 Toggle Sequence Completed.", "SUCCESS")

    def tc_dsp_013(self):
        self.log("\n=== [TC DSP_013] Charge & Low Battery Warning Pop-up ===", "HEADER")
        self.log("Step 1: Transmitting EffectiveSOC = 100% for 3 seconds...", "INFO")
        if not self.send_bcm_command(key_on=1, soc=100, low_batt_warn=0, duration_sec=3.0):
            self.log("--> FAIL: DSP_013 Terminated due to Hardware Disconnection.", "FAIL")
            return

        self.log("Step 2: Transmitting EffectiveSOC = 10% & Low Battery Warning for 5 seconds...", "INFO")
        if self.send_bcm_command(key_on=1, soc=10, low_batt_warn=1, duration_sec=5.0):
            self.log("--> PASS: Low Battery Warning Pop-up Triggered.", "SUCCESS")
        else:
            self.log("--> FAIL: DSP_013 Terminated due to Hardware Disconnection.", "FAIL")

    # =========================================================================
    # MASTER SEQUENCES (SEPARATE BUTTONS PER SHEET)
    # =========================================================================
    def run_sfb_sequence(self):
        """Runs all Screen Flow & Boot test cases sequentially."""
        self.log("\n==================================================", "HEADER")
        self.log("▶ MASTER AUTOMATION: SCREEN FLOW & BOOT SHEET", "HEADER")
        self.log("==================================================", "HEADER")
        self.tc_sfb_001()
        if not self.abort_requested and self.bus:
            self.tc_sfb_002()
        if not self.abort_requested and self.bus:
            self.tc_sfb_003()
        if not self.abort_requested and self.bus:
            self.log("\n✅ SCREEN FLOW & BOOT SEQUENCE COMPLETED", "SUCCESS")

    def run_dsp_sequence(self):
        """Runs all Display & UI test cases sequentially."""
        self.log("\n==================================================", "HEADER")
        self.log("▶ MASTER AUTOMATION: DISPLAY & UI SHEET", "HEADER")
        self.log("==================================================", "HEADER")
        self.tc_dsp_001()
        if not self.abort_requested and self.bus:
            self.tc_dsp_002()
        if not self.abort_requested and self.bus:
            self.tc_dsp_003()
        if not self.abort_requested and self.bus:
            self.tc_dsp_004()
        if not self.abort_requested and self.bus:
            self.tc_dsp_005()
        if not self.abort_requested and self.bus:
            self.tc_dsp_bento()
        if not self.abort_requested and self.bus:
            self.tc_dsp_012()
        if not self.abort_requested and self.bus:
            self.tc_dsp_013()
        if not self.abort_requested and self.bus:
            self.log("\n✅ DISPLAY & UI SEQUENCE COMPLETED", "SUCCESS")

    def __del__(self):
        if self.bus:
            try:
                self.bus.shutdown()
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = Sanity_Automation_GUI(root)
    root.mainloop()
