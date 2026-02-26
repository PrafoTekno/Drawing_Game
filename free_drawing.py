import cv2
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

drawn_platforms = []

# ------------------------- # Pointer cursor + highlight # -------------------------
pointer = Entity( parent=camera.ui, 
                 model='sphere', 
                 scale=0.06, 
                 color=color.red, 
                 enabled=False 
                 ) 

def smooth(old, new, factor=0.18): 
    return old + (new - old) * factor 

# ------------------------- # 2D UI mapping + projection # ------------------------- 
def cam_to_ui(px, py, img_w, img_h): 
    nx = px/img_w 
    ny = py/img_h 
    return Vec3( (nx-0.5)*0.9, (0.5-ny)*0.9, 0 )

Developer_text = Text (
    "Created by PrafoTekno",
    position=Vec2(0.45, 0.45),
    scale=1,
    color=rgb(1,1,1)
)

command_text = Text (
    "index finger for drawing, index and mid fing to delete",
    position=Vec2(0.18, 0.40),
    scale=1,
    color=rgb(1,1,1)
)

def update():

    fps_text.text = f"FPS: {int(1 / time.dt)}"

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

    if right and right.get("lmList") and len(right["lmList"]) >= 21:

        thumb_up  = right["lmList"][4][0] < right["lmList"][3][0]     # right hand
        index_up  = right["lmList"][8][1] < right["lmList"][6][1]
        middle_up = right["lmList"][12][1] < right["lmList"][10][1]
        ring_up   = right["lmList"][16][1] < right["lmList"][14][1]
        pinky_up  = right["lmList"][20][1] < right["lmList"][18][1]

        if not thumb_up and middle_up and index_up and not ring_up and not pinky_up:
            current_mode_R = "delete"
        elif not middle_up and not ring_up and not pinky_up and not thumb_up and index_up:
            current_mode_R = "drawing"
        elif not middle_up and not ring_up and not pinky_up and thumb_up and not index_up:
            current_mode_R = "switch_obj"
        else:
            current_mode_R = "none"

    if current_mode_R == "drawing":

        lm = right["lmList"]
        index = lm[8]

        # ---- Convert finger tip to UI space ----
        ui_pt = cam_to_ui(index[0], index[1], w, h)

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
                    scale=brush_size,
                    color=brush_color,
                    position=pos
                )
                drawn_platforms.append (plat)

        last_draw_pos = ui_pt

    else:
        pointer.enabled = False
        last_draw_pos = None
    
    if current_mode_R == "delete":
        for p in drawn_platforms:
            destroy(p)
        drawn_platforms.clear()

    # ============================================================
    # ================= Hand Visualization Update ================
    # ============================================================
    if hands:
        lm = hands[0]["lmList"]
        norm = [(lm[i][0], lm[i][1], 0) for i in range(21)]
        hand_vis.update(norm, lambda x,y,z: cam_to_ui(x,y,w,h)) 
    else:
        hand_vis.hide()

    cv2.imshow("cvzone", img)
    if cv2.waitKey(1)&0xFF==ord('q'):
        application.quit()

def input(key):
    if key=='escape':
        application.quit()

app.run()
cv2.destroyAllWindows()
cap.release()


    
