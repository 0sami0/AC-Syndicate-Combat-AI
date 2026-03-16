import cv2
import numpy as np
import mss
import pydirectinput
import keyboard
import time
import tkinter as tk
import ctypes
import os
import sys
import glob 
import threading

pydirectinput.FAILSAFE = False

# =========================================================
# 1. LOAD ALL TEMPLATES (DYNAMIC BANKS)
# =========================================================

def load_template_bank(file_pattern, threshold_bw=False):
    files = glob.glob(file_pattern)
    templates =[]
    for f in files:
        raw_img = cv2.imread(f, 0)
        if raw_img is None: continue
        if threshold_bw:
            _, final_img = cv2.threshold(raw_img, 200, 255, cv2.THRESH_BINARY)
        else:
            final_img = raw_img
        templates.append(final_img)
    return templates

print("[*] Loading AI Image Banks...")
ui_templates = load_template_bank('counter_template.png', threshold_bw=True)
if not ui_templates:
    print("[ERROR] Missing counter_template.png!")
    sys.exit()
ui_template = ui_templates[0]

attack_templates  = load_template_bank('attack_*.png', threshold_bw=True)   
eprompt_templates = load_template_bank('eprompt_*.png', threshold_bw=True)  
dodge_templates   = load_template_bank('dodge_*.png', threshold_bw=True)    
guard_templates   = load_template_bank('guard_*.png', threshold_bw=False)   
space_templates   = load_template_bank('space_*.png', threshold_bw=True)    

print(f"[+] Loaded {len(attack_templates)} Yellow Attack templates")
print(f"[+] Loaded {len(eprompt_templates)} 'E' Prompt templates")
print(f"[+] Loaded {len(dodge_templates)} Dodge templates")
print(f"[+] Loaded {len(guard_templates)} Guard templates")
print(f"[+] Loaded {len(space_templates)} Space templates")

# =========================================================
# 2. THREADING GLOBALS
# =========================================================
in_combat_global = False
is_defending_global = False  # Tells the mouse to stop clicking!
ui_draw_data = None 

# =========================================================
# 3. COMBAT ACTION WORKERS (THE "HANDS")
# =========================================================

def trigger_defense(key):
    """ Executes 3 clicks over exactly 1 second, pausing auto-attacks """
    global is_defending_global
    
    is_defending_global = True           # 1. Instantly pause auto-attacking
    pydirectinput.mouseUp(button='left') # 2. Release left click so we don't drop the defense
    
    # 3 presses * ~0.33s = ~1.0 second total defense sequence
    for _ in range(3):
        pydirectinput.keyDown(key)
        time.sleep(0.03)
        pydirectinput.keyUp(key)
        time.sleep(0.30) 
        
    is_defending_global = False          # 3. Resume auto-attacking instantly!

def auto_attack_worker():
    """ Runs constantly in the background, spamming click every 0.1s unless defending """
    while True:
        if in_combat_global and not is_defending_global:
            pydirectinput.mouseDown(button='left')
            time.sleep(0.02)
            pydirectinput.mouseUp(button='left')
            time.sleep(0.08) # 0.02 + 0.08 = 0.1s per click
        else:
            # If idle or defending, just wait 10ms and check again
            time.sleep(0.01)

# Start the Auto-Attacker Thread
threading.Thread(target=auto_attack_worker, daemon=True).start()

def emergency_stop():
    keyboard.wait('end')
    print("\n[!] END PRESSED. SHUTTING DOWN SYSTEM.")
    pydirectinput.mouseUp(button='left')
    os._exit(0)

threading.Thread(target=emergency_stop, daemon=True).start()

# =========================================================
# 4. THE AI BRAIN (RUNS AT MAX FPS IN BACKGROUND)
# =========================================================

def ai_brain_loop():
    global in_combat_global, ui_draw_data
    
    zone_full = {"top": 0, "left": 0, "width": 1440, "height": 900}
    
    lower_yellow = np.array([10, 100, 180])
    upper_yellow = np.array([40, 255, 255])
    lower_pale = np.array([10, 0, 200])
    upper_pale = np.array([40, 150, 255])

    last_combat_time = 0
    last_ui_check_time = 0
    last_defense_time = 0
    last_draw_time = 0
    
    COOLDOWN = 1.0 # Wait exactly 1 second (while the 3 keys are being pressed) before finding the next attack

    print("\n[+] AC SYNDICATE THREADED AI ACTIVE! AUTO-SPAM & 1s DEFENSES ENABLED.")
    print("[+] Press 'END' to completely exit.")

    with mss.mss() as sct:
        while True:
            current_time = time.time()

            # --- COMBAT CHECK (10 FPS Check) ---
            if current_time - last_ui_check_time > 0.1:
                img_full = np.array(sct.grab(zone_full))
                img_ui = img_full[600:900, 1000:1400]
                
                gray_ui = cv2.cvtColor(img_ui, cv2.COLOR_BGR2GRAY)
                _, bw_ui = cv2.threshold(gray_ui, 200, 255, cv2.THRESH_BINARY)
                res_ui = cv2.matchTemplate(bw_ui, ui_template, cv2.TM_CCOEFF_NORMED)
                _, max_val_ui, _, _ = cv2.minMaxLoc(res_ui)

                if max_val_ui >= 0.80:
                    last_combat_time = current_time
                last_ui_check_time = current_time

            in_combat_global = (current_time - last_combat_time) < 2.0

            # --- DEFENSE CHECK ---
            # If 1.0s has passed since our last defense, the brain looks for new threats
            if in_combat_global and (current_time - last_defense_time > COOLDOWN):
                img_full = np.array(sct.grab(zone_full))
                hsv_full = cv2.cvtColor(img_full, cv2.COLOR_BGR2HSV)
                gray_full = cv2.cvtColor(img_full, cv2.COLOR_BGR2GRAY)
                _, bw_full = cv2.threshold(gray_full, 200, 255, cv2.THRESH_BINARY)
                
                action_triggered = False

                # 1. PARRY ('E')
                draw_x, draw_y, draw_w, draw_h = 0, 0, 0, 0
                mask_y = cv2.inRange(hsv_full, lower_yellow, upper_yellow)
                mask_p = cv2.inRange(hsv_full, lower_pale, upper_pale)
                mask_combined = cv2.bitwise_or(mask_y, mask_p)

                for atk_temp in attack_templates:
                    res_atk = cv2.matchTemplate(mask_combined, atk_temp, cv2.TM_CCOEFF_NORMED)
                    _, max_val_atk, _, max_loc_atk = cv2.minMaxLoc(res_atk)
                    if max_val_atk >= 0.64:
                        action_triggered = True
                        draw_x, draw_y = max_loc_atk
                        draw_h, draw_w = atk_temp.shape
                        break 

                if not action_triggered:
                    for e_temp in eprompt_templates:
                        res_e = cv2.matchTemplate(bw_full, e_temp, cv2.TM_CCOEFF_NORMED)
                        _, max_val_e, _, max_loc_e = cv2.minMaxLoc(res_e)
                        if max_val_e >= 0.80:
                            action_triggered = True
                            draw_x, draw_y = max_loc_e
                            draw_h, draw_w = e_temp.shape
                            break

                if action_triggered:
                    ui_draw_data = {'x': draw_x, 'y': draw_y, 'w': draw_w, 'h': draw_h, 'c': 'magenta', 't': 'DEFLECT!'}
                    last_draw_time = current_time
                    last_defense_time = current_time
                    threading.Thread(target=trigger_defense, args=('e',), daemon=True).start()
                    continue # Skip checking Dodge/Guard since we are already Deflecting

                # 2. DODGE ('F') 
                if not action_triggered:
                    bw_dodge = bw_full[200:700, 500:940]
                    for ddg_temp in dodge_templates:
                        res_ddg = cv2.matchTemplate(bw_dodge, ddg_temp, cv2.TM_CCOEFF_NORMED)
                        _, max_val_ddg, _, max_loc_ddg = cv2.minMaxLoc(res_ddg)

                        if max_val_ddg >= 0.79: 
                            draw_h, draw_w = ddg_temp.shape
                            ui_draw_data = {'x': 500+max_loc_ddg[0], 'y': 200+max_loc_ddg[1], 'w': draw_w, 'h': draw_h, 'c': 'blue', 't': 'DODGE F!'}
                            last_draw_time = current_time
                            last_defense_time = current_time
                            action_triggered = True
                            threading.Thread(target=trigger_defense, args=('f',), daemon=True).start()
                            break
                
                if action_triggered: continue

                # 3. GUARD BREAK ('SPACE')
                if not action_triggered:
                    for grd_temp in guard_templates:
                        res_grd = cv2.matchTemplate(gray_full, grd_temp, cv2.TM_CCOEFF_NORMED)
                        _, max_val_grd, _, max_loc_grd = cv2.minMaxLoc(res_grd)
                        if max_val_grd >= 0.65: 
                            action_triggered = True
                            draw_x, draw_y = max_loc_grd
                            draw_h, draw_w = grd_temp.shape
                            break
                    
                    if not action_triggered:
                        bw_combat = bw_full[100:800, 100:1340]
                        for spc_temp in space_templates:
                            res_spc = cv2.matchTemplate(bw_combat, spc_temp, cv2.TM_CCOEFF_NORMED)
                            _, max_val_spc, _, max_loc_spc = cv2.minMaxLoc(res_spc)
                            if max_val_spc >= 0.70:
                                action_triggered = True
                                draw_x, draw_y = 100+max_loc_spc[0], 100+max_loc_spc[1]
                                draw_h, draw_w = spc_temp.shape
                                break

                    if action_triggered:
                        ui_draw_data = {'x': draw_x, 'y': draw_y, 'w': draw_w, 'h': draw_h, 'c': 'orange', 't': 'GUARD BREAK!'}
                        last_draw_time = current_time
                        last_defense_time = current_time
                        threading.Thread(target=trigger_defense, args=('space',), daemon=True).start()

            # Clear UI if it's been visible for more than 0.3 seconds
            if ui_draw_data and (current_time - last_draw_time > 0.3):
                ui_draw_data = None

# START THE AI BRAIN IN A BACKGROUND THREAD
threading.Thread(target=ai_brain_loop, daemon=True).start()

# =========================================================
# 5. TKINTER RENDERING ENGINE (RUNS ON MAIN THREAD AT 60 FPS)
# =========================================================

root = tk.Tk()
root.title("AC AI Master Overlay")
root.geometry("1440x900+0+0")
root.overrideredirect(True)
root.wm_attributes("-topmost", True)
root.wm_attributes("-transparentcolor", "black")
root.config(bg="black")

hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x00080020)

canvas = tk.Canvas(root, width=1440, height=900, bg="black", highlightthickness=0)
canvas.pack()

def update_gui_loop():
    """ Safely draws the boxes without slowing down the CV2 math """
    canvas.delete("all")
    
    if in_combat_global:
        if is_defending_global:
            canvas.create_text(720, 50, text="[ COMBAT : DEFENDING ]", fill="orange", font=("Arial", 16, "bold"))
        else:
            canvas.create_text(720, 50, text="[ COMBAT : SPAMMING ATTACK ]", fill="red", font=("Arial", 16, "bold"))
    else:
        canvas.create_text(720, 50, text="[ IDLE ]", fill="white", font=("Arial", 14))
        
    if ui_draw_data:
        d = ui_draw_data
        canvas.create_rectangle(d['x'], d['y'], d['x']+d['w'], d['y']+d['h'], outline=d['c'], width=3)
        canvas.create_text(d['x'] + (d['w']/2), d['y'] - 15, text=d['t'], fill=d['c'], font=("Arial", 14, "bold"))
        
    root.after(16, update_gui_loop)

update_gui_loop()
root.mainloop()