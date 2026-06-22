import cv2
import numpy as np
import winsound

def play_beep_sound(success=True):
    """
    Plays native Windows beep sounds for feedback.
    """
    try:
        if success:
            # High-pitched pleasant success double beep
            winsound.Beep(1200, 100)
            winsound.Beep(1500, 150)
        else:
            # Low-pitched error beep
            winsound.Beep(400, 250)
    except Exception:
        pass  # Fallback if audio device is unavailable

def draw_premium_hud(frame, active_gesture, hold_ratio, student_name, last_log_message):
    """
    Draws a modern, glassmorphic HUD on the frame.
    Colors:
    - Background/HUD: Deep Charcoal / Dark Blue (semi-transparent)
    - Active State: Neon Green/Cyan
    - Text: Crisp White
    """
    h, w, _ = frame.shape
    
    # 1. Draw top semi-transparent glass header
    header_h = 70
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, header_h), (30, 25, 20), -1)
    
    # 2. Draw bottom status bar
    footer_h = 60
    cv2.rectangle(overlay, (0, h - footer_h), (w, h), (20, 20, 20), -1)
    
    # Apply transparency to header and footer
    alpha = 0.75
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    # Add neon Accent line at the bottom of header
    cv2.line(frame, (0, header_h), (w, header_h), (0, 230, 230), 2)  # Cyan line
    # Add neon Accent line at the top of footer
    cv2.line(frame, (0, h - footer_h), (w, h - footer_h), (0, 230, 230), 2)
    
    # 3. Add Header text
    cv2.putText(frame, "AI SMART ATTENDANCE SYSTEM", (20, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Display current student name
    name_display = f"STUDENT: {student_name.upper()}" if student_name else "STUDENT: NOT REGISTERED"
    cv2.putText(frame, name_display, (w - 320, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                
    # 4. Add Footer text (status / log messages)
    log_color = (0, 255, 0) if "Success" in last_log_message else (255, 255, 255)
    if "Already" in last_log_message or "Error" in last_log_message:
        log_color = (0, 165, 255)  # Orange/Amber warning
        
    cv2.putText(frame, last_log_message.upper(), (20, h - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, log_color, 2, cv2.LINE_AA)
                
    # Display controls helper on the bottom right
    cv2.putText(frame, "Q: QUIT | ESC: RESET", (w - 220, h - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

    # 5. Draw Progress Bar for holding a gesture
    if hold_ratio > 0.0:
        bar_w = 400
        bar_h = 24
        bar_x = (w - bar_w) // 2
        bar_y = h - footer_h - 45
        
        # Draw background bar (dark grey)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        
        # Draw progress bar fill (gradient look using outline + filled rectangle)
        fill_w = int(bar_w * hold_ratio)
        
        # Color transition from Amber/Yellow to Green based on hold progress
        bar_color = (0, int(150 + 105 * hold_ratio), int(255 - 255 * hold_ratio))  # Transition Orange -> Green
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), bar_color, -1)
        # Draw border
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (255, 255, 255), 2)
        
        # Draw text inside/above bar
        label_text = f"HOLDING GESTURE: {active_gesture.upper()} ({int(hold_ratio * 100)}%)"
        cv2.putText(frame, label_text, (bar_x + 10, bar_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

def draw_corner_rect(frame, bbox, color=(0, 255, 0), thickness=2, length=20):
    """
    Draws a premium bounding box with styled corners instead of a full rectangle.
    """
    x1, y1, x2, y2 = bbox
    
    # Draw thin boundary rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)
    
    # Top-Left corner
    cv2.line(frame, (x1, y1), (x1 + length, y1), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1, y1), (x1, y1 + length), color, thickness, cv2.LINE_AA)
    
    # Top-Right corner
    cv2.line(frame, (x2, y1), (x2 - length, y1), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y1), (x2, y1 + length), color, thickness, cv2.LINE_AA)
    
    # Bottom-Left corner
    cv2.line(frame, (x1, y2), (x1 + length, y2), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1, y2), (x1, y2 - length), color, thickness, cv2.LINE_AA)
    
    # Bottom-Right corner
    cv2.line(frame, (x2, y2), (x2 - length, y2), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2, y2 - length), color, thickness, cv2.LINE_AA)
