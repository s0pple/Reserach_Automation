import json
import time
import os
import sys
import logging
import cv2
import numpy as np
import pyautogui
import mss

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [CV_BOT] - %(message)s')

def execute_cv_workflow(workflow_json_path):
    if not os.path.exists(workflow_json_path):
        logging.error(f"Workflow file not found: {workflow_json_path}")
        return False
        
    with open(workflow_json_path, 'r') as f:
        workflow = json.load(f)
        
    logging.info(f"Starting CV Workflow with {len(workflow)} steps.")
    
    with mss.mss() as sct:
        monitor = sct.monitors[1] # Primary monitor
        
        for step_data in workflow:
            step_idx = step_data.get('step')
            action = step_data.get('action')
            template_path = step_data.get('template_image')
            
            logging.info(f"Executing Step {step_idx}: {action} using template {template_path}")
            
            if not os.path.exists(template_path):
                logging.error(f"Template image missing: {template_path}. Skipping step.")
                continue
                
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                logging.error(f"Could not read template: {template_path}")
                continue
                
            # Try to find the template on screen
            found = False
            start_time = time.time()
            timeout = 5.0 # Wait up to 5 seconds for the element to appear
            
            while time.time() - start_time < timeout:
                screenshot = sct.grab(monitor)
                img_np = cv2.cvtColor(np.frombuffer(screenshot.bgra, dtype=np.uint8).reshape(screenshot.height, screenshot.width, 4), cv2.COLOR_BGRA2BGR)
                
                result = cv2.matchTemplate(img_np, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                if max_val >= 0.8: # 80% confidence
                    found = True
                    # Calculate center
                    x = monitor['left'] + max_loc[0] + template.shape[1] // 2
                    y = monitor['top'] + max_loc[1] + template.shape[0] // 2
                    
                    logging.info(f"Match found! Confidence: {max_val:.2f} at ({x}, {y})")
                    
                    if action == 'click':
                        pyautogui.click(x, y)
                    elif action == 'hover':
                        pyautogui.moveTo(x, y)
                    
                    time.sleep(1) # Short delay after action
                    break
                    
                time.sleep(0.1)
                
            if not found:
                logging.error(f"Step {step_idx} failed: Template not found on screen within timeout. Self-Healing would trigger here!")
                return False
                
    logging.info("🎉 CV Workflow completed successfully!")
    return True

if __name__ == "__main__":
    workflow_path = "temp/workflow/workflow_log.json"
    execute_cv_workflow(workflow_path)