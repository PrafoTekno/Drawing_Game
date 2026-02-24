
import cv2
import random
from cvzone.HandTrackingModule import HandDetector
from ursina import *

# -------------------------
# CVZone setup
# -------------------------
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

detector = HandDetector(detectionCon=0.7, maxHands=2)
thumb_up  = False       # left hand (reverse for right hand)
index_up  = False 
middle_up = False 
ring_up   = False 
pinky_up  = False 

# -------------------------
# Ursina setup
# -------------------------
app = Ursina()
window.color = color.rgb(30/255, 30/255, 30/255)
#window.show_fps = True
fps_text = Text(position=(-0.85, 0.45), scale=1)

# -------------------------
# Hand Visualization (UI)
# -------------------------
class HandVisualization:
    def __init__(self):
        self.lms = [Entity(parent=camera.ui, model='sphere', color=color.azure, scale=0.03, enabled=False) for _ in range(21)]

        self.CONN = [
            (0,1),(1,2),(2,3),(3,4),
            (0,5),(5,6),(6,7),(7,8),
            (5,9),(9,10),(10,11),(11,12),
            (9,13),(13,14),(14,15),(15,16),
            (13,17),(17,18),(18,19),(19,20),
            (0,17)
        ]
        self.bones = [Entity(parent=camera.ui, model='cube', color=color.orange, scale=(0.02,0.02,1), enabled=False)
                      for _ in self.CONN]

    def update(self, lm, cam_to_ui_fn):
        if lm is None:
            self.hide()
            return

        pts = [cam_to_ui_fn(x,y,z) for (x,y,z) in lm]

        for i,p in enumerate(pts):
            self.lms[i].position = p
            self.lms[i].enabled = True

        for i,(a,b) in enumerate(self.CONN):
            p1 = pts[a]
            p2 = pts[b]
            bone = self.bones[i]
            mid = (p1+p2)/2
            bone.position = mid
            bone.look_at(p2)
            bone.scale_z = max(0.001, distance(p1,p2))
            bone.enabled = True

    def hide(self):
        for s in self.lms: s.enabled=False
        for b in self.bones: b.enabled=False

hand_vis = HandVisualization()

# -------------------------
# Drawing config
# -------------------------
brush_size = 0.02
brush_color = color.white
last_draw_pos = None

# -------------------------
# Platform storage
# -------------------------
drawn_platforms = []

# -------------------------
# Ball spawn
# -------------------------
ball_spawn = Vec2(0.4, 0.35)

# -------------------------
# Ball setup
# -------------------------
ball = Entity(
    parent=camera.ui,
    model='circle',
    color=color.orange,
    scale=0.04,
    position=ball_spawn
)

ball_vel = Vec2(0, 0)
gravity = 0 #-0.00015

# -------------------------
# Bucket goal
# -------------------------
bucket_pos = Vec2(0, -0.35)
bucket = Entity(
    parent=camera.ui,
    model='quad',
    color=color.green,
    scale=(0.12, 0.08),
    position=bucket_pos
)

bucket_text = Text(
    "GOAL",
    parent=bucket,
    y=0.6,
    origin=(0,0),
    scale=10
)

Developer_text = Text (
    "Created by PrafoTekno",
    position=Vec2(0.45, 0.45),
    scale=1,
    color=rgb(1,1,1)
)

# ------------------------- # Pointer + cursor + highlight # -------------------------
pointer = Entity( parent=camera.ui, 
                 model='sphere', 
                 scale=0.06, 
                 color=color.red, 
                 enabled=False 
                 ) 

cursor = Entity( parent=camera.ui, 
                 model='sphere', 
                 scale=0.06, 
                 color=color.green, 
                 enabled=False 
                 ) 

button = Entity( parent=camera.ui,
                 position= Vec2(-0.35, 0.35), 
                 model='quad', 
                 scale=(0.12, 0.12), 
                 color=rgb(250/255,200/255,80/255), 
                 enabled=True 
                 ) 
bucket_text = Text(
    "START",
    parent=button,
    origin=(0,0),
    color=color.black,
    scale=10
)

def smooth(old, new, factor=0.18): 
    return old + (new - old) * factor 

# ------------------------- # 2D UI mapping + projection # ------------------------- 
def cam_to_ui(px, py, img_w, img_h): 
    nx = px/img_w 
    ny = py/img_h 
    return Vec3( (nx-0.5)*0.9, (0.5-ny)*0.9, 0 )

def update():

    fps_text.text = f"FPS: {int(1 / time.dt)}"

    global selected_box, is_grabbing, last_right_count, count_fing_up
    global rotation_speed_x, rotation_speed_y, reference_x, reference_y, hand_active
    global ref_pan_x, ref_pan_y, hand_pan_active, previous_mode, position_speed_x, position_speed_z
    global zoom_speed, max_zoom, min_zoom, zoom_amount, pinch_reference, zoom_active
    global thumb_up, index_up, middle_up, ring_up, pinky_up
    global highlight_box, pan_velocity, target_move, forward_dir
    global c1, c2, cR

    success, img = cap.read()
    if not success:
        return

    img = cv2.flip(img, 1)
    h, w = img.shape[:2]
    #print (f"h = {h} | w = {w}")

    # Detect hands (flipType=False because we already flipped manually)
    hands, img = detector.findHands(img, draw=True, flipType=False)

    # Fix handedness due to manual flip
    def fix_type(hnd):
        return "Left" if hnd["type"] == "Right" else "Right"

    left = None
    right = None

    if hands:
        for hnd in hands:
            t = fix_type(hnd)
            if t == "Right":
                left = hnd
            else:
                right = hnd


    # ------------- WHICH FINGER UP LEFT -----------------------
    current_mode_R = "none"
    current_mode_L = "none"

    if right and right.get("lmList") and len(right["lmList"]) >= 21:

        thumb_up  = right["lmList"][4][0] < right["lmList"][3][0]     # right hand
        index_up  = right["lmList"][8][1] < right["lmList"][6][1]
        middle_up = right["lmList"][12][1] < right["lmList"][10][1]
        ring_up   = right["lmList"][16][1] < right["lmList"][14][1]
        pinky_up  = right["lmList"][20][1] < right["lmList"][18][1]

        if not middle_up and not ring_up and not pinky_up:
            current_mode_R = "drawing"
        elif thumb_up and index_up and middle_up and ring_up and pinky_up:
            current_mode_R = "remove"
        else:
            current_mode_R = "none"

    if left and left.get("lmList") and len(left["lmList"]) >= 21:

        thumb_up  = left["lmList"][4][0] > left["lmList"][3][0]     # left hand
        index_up  = left["lmList"][8][1] < left["lmList"][6][1]
        middle_up = left["lmList"][12][1] < left["lmList"][10][1]
        ring_up   = left["lmList"][16][1] < left["lmList"][14][1]
        pinky_up  = left["lmList"][20][1] < left["lmList"][18][1]

        if not middle_up and not ring_up and not pinky_up and not thumb_up:
            current_mode_L = "click"
        elif thumb_up and index_up and middle_up and ring_up and pinky_up:
            current_mode_L = "remove"
        else:
            current_mode_L = "none"

    if current_mode_R == "drawing":
        
        lm = right["lmList"]
        index_R = lm[8]
        # ---- Convert finger tip to UI space ----
        ui_pt = cam_to_ui(index_R[0], index_R[1], w, h)

        # ---- Show pointer ----
        pointer.enabled = True
        pointer.position = ui_pt

        # ---- Interpolated drawing ----
        global last_draw_pos

        if last_draw_pos:
            dist = distance(ui_pt, last_draw_pos)
            steps = int(dist / brush_size) + 1

            for i in range(steps):
                pos = lerp(last_draw_pos, ui_pt, i / steps)
                plat = Entity(
                    parent=camera.ui,
                    model='quad',
                    scale=(brush_size*2, brush_size*0.6),
                    color=brush_color,
                    position=pos
                )
                drawn_platforms.append(plat)

        last_draw_pos = ui_pt

    else:
        pointer.enabled = False
        last_draw_pos = None
    
    if current_mode_R == "remove":
        for p in drawn_platforms:
            destroy(p)
        drawn_platforms.clear()

    global gravity

    if current_mode_L == 'click':

        lm = left["lmList"]
        index_L = lm[8]
        # ---- Convert finger tip to UI space ----
        ui_pt = cam_to_ui(index_L[0], index_L[1], w, h)

        cursor.enabled = True
        cursor.position = ui_pt

        if button.x-0.12 <= cursor.x <= button.x+0.12 and button.y-0.12 <= cursor.y <= button.y+0.12:
            gravity = -0.00015
        else:
            gravity = 0

    # ============================================================
    # ================= Hand Visualization Update ================
    # ============================================================
    if hands:
        lm = hands[0]["lmList"]
        norm = [(lm[i][0], lm[i][1], 0) for i in range(21)]
        hand_vis.update(norm, lambda x,y,z: cam_to_ui(x,y,w,h)) 
    else:
        hand_vis.hide()

    # ================= BALL PHYSICS =================

    global ball_vel

    # gravity
    ball_vel.y += gravity
    ball.y += ball_vel.y
    ball.x += ball_vel.x

    # collision with platforms
    for p in drawn_platforms:
        dx = ball.x - p.x
        dy = ball.y - p.y

        if abs(dx) < p.scale_x/2 and abs(dy) < p.scale_y/2:
            if ball_vel.y < 0:
                ball.y = p.y + p.scale_y/2 + ball.scale_y/2
                # simulate rolling
                slope = dx * 0.05
                ball_vel.x += slope
                ball_vel.y = 0

    ball_vel.x *= 0.99

    if distance (ball.position, bucket.position) < 0.08:
        print ("WIN")

        ball.position = ball_spawn
        ball_vel = Vec2(0, 0)

        bucket.x = random.uniform(-0.5, 0.5)

        for p in drawn_platforms:
            destroy(p)
        drawn_platforms.clear()

    # reset if fall
    if ball.y < -0.5:
        ball.position = ball_spawn
        ball_vel = Vec2(0, 0)

    cv2.imshow("cvzone", img)
    if cv2.waitKey(1)&0xFF==ord('q'):
        application.quit()

def input(key):
    if key=='escape':
        application.quit()

app.run()
cv2.destroyAllWindows()
cap.release()


    