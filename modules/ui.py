import os
import webbrowser
import customtkinter as ctk
from typing import Callable, Tuple
import cv2
from PIL import Image, ImageOps
import tkinterdnd2 as tkdnd

import modules.globals
import modules.metadata
from modules.face_analyser import (
    get_one_face,
    get_unique_faces_from_target_image,
    get_unique_faces_from_target_video,
    add_blank_map,
    has_valid_map,
    simplify_maps,
)
from modules.capturer import get_video_frame, get_video_frame_total
from modules.processors.frame.core import get_frame_processors_modules
from modules.utilities import (
    is_image,
    is_video,
    resolve_relative_path,
    has_image_extension,
)

ROOT = None
POPUP = None
POPUP_LIVE = None
ROOT_HEIGHT = 700
ROOT_WIDTH = 600

PREVIEW = None
PREVIEW_MAX_HEIGHT = 700
PREVIEW_MAX_WIDTH = 1200
PREVIEW_DEFAULT_WIDTH = 960
PREVIEW_DEFAULT_HEIGHT = 540

POPUP_WIDTH = 750
POPUP_HEIGHT = 810
POPUP_SCROLL_WIDTH = 740
POPUP_SCROLL_HEIGHT = 700

POPUP_LIVE_WIDTH = 900
POPUP_LIVE_HEIGHT = 820
POPUP_LIVE_SCROLL_WIDTH = 890
POPUP_LIVE_SCROLL_HEIGHT = 700

MAPPER_PREVIEW_MAX_HEIGHT = 100
MAPPER_PREVIEW_MAX_WIDTH = 100

DEFAULT_BUTTON_WIDTH = 200
DEFAULT_BUTTON_HEIGHT = 40

RECENT_DIRECTORY_SOURCE = None
RECENT_DIRECTORY_TARGET = None
RECENT_DIRECTORY_OUTPUT = None

preview_label = None
preview_slider = None
source_label = None
target_label = None
status_label = None
popup_status_label = None
popup_status_label_live = None
source_label_dict = {}
source_label_dict_live = {}
target_label_dict_live = {}

img_ft, vid_ft = modules.globals.file_types


class DragDropButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.drop_target_register(tkdnd.DND_FILES)
        self.dnd_bind("<<Drop>>", self.drop)

    def drop(self, event):
        file_path = event.data
        if file_path.startswith("{"):
            file_path = file_path[1:-1]
        self.handle_drop(file_path)

    def handle_drop(self, file_path):
        pass


class SourceButton(DragDropButton):
    def handle_drop(self, file_path):
        if is_image(file_path):
            modules.globals.source_path = file_path
            global RECENT_DIRECTORY_SOURCE
            RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
            image = render_image_preview(modules.globals.source_path, (200, 200))
            source_label.configure(image=image)
            source_label.configure(text="")


class SourceMapperButton(DragDropButton):
    def __init__(self, master, map, button_num, **kwargs):
        super().__init__(master, **kwargs)
        self.map = map
        self.button_num = button_num

    def handle_drop(self, file_path):
        if is_image(file_path):
            update_popup_source(self.master, self.map, self.button_num, file_path)


class TargetButton(DragDropButton):
    def handle_drop(self, file_path):
        global RECENT_DIRECTORY_TARGET
        if is_image(file_path) or is_video(file_path):
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
            if is_image(file_path):
                image = render_image_preview(modules.globals.target_path, (200, 200))
                target_label.configure(image=image)
                target_label.configure(text="")
            elif is_video(file_path):
                video_frame = render_video_preview(file_path, (200, 200))
                target_label.configure(image=video_frame)
                target_label.configure(text="")


class DragDropLabel(ctk.CTkLabel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.drop_target_register(tkdnd.DND_FILES)
        self.dnd_bind("<<Drop>>", self.drop)

    def drop(self, event):
        file_path = event.data
        if file_path.startswith("{"):
            file_path = file_path[1:-1]
        self.handle_drop(file_path)

    def handle_drop(self, file_path):
        pass


class SourceLabel(DragDropLabel):
    def handle_drop(self, file_path):
        if is_image(file_path):
            modules.globals.source_path = file_path
            global RECENT_DIRECTORY_SOURCE
            RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
            image = render_image_preview(modules.globals.source_path, (200, 200))
            source_label.configure(image=image)
            source_label.configure(text="")


class TargetLabel(DragDropLabel):
    def handle_drop(self, file_path):
        global RECENT_DIRECTORY_TARGET
        if is_image(file_path) or is_video(file_path):
            modules.globals.target_path = file_path
            RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
            if is_image(file_path):
                image = render_image_preview(modules.globals.target_path, (200, 200))
                target_label.configure(image=image)
                target_label.configure(text="")
            elif is_video(file_path):
                video_frame = render_video_preview(file_path, (200, 200))
                target_label.configure(image=video_frame)
                target_label.configure(text="")


def init(start: Callable[[], None], destroy: Callable[[], None]) -> tkdnd.TkinterDnD.Tk:
    global ROOT, PREVIEW

    ROOT = create_root(start, destroy)
    PREVIEW = create_preview(ROOT)

    return ROOT


def create_root(
    start: Callable[[], None], destroy: Callable[[], None]
) -> tkdnd.TkinterDnD.Tk:
    global source_label, target_label, status_label

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")  # Use a built-in theme

    root = tkdnd.TkinterDnD.Tk()
    root.minsize(ROOT_WIDTH, ROOT_HEIGHT)
    root.title(
        f"{modules.metadata.name} {modules.metadata.version} {modules.metadata.edition}"
    )
    root.configure(bg="gray12")
    root.protocol("WM_DELETE_WINDOW", lambda: destroy())

    source_label = SourceLabel(
        root,
        text="Drag & Drop\nSource Image Here",
        text_color="gray",
        font=("Arial", 16),
        justify="center",
    )
    source_label.place(relx=0.1, rely=0.1, relwidth=0.3, relheight=0.25)

    target_label = TargetLabel(
        root,
        text="Drag & Drop\nTarget Image/Video Here",
        text_color="gray",
        font=("Arial", 16),
        justify="center",
    )
    target_label.place(relx=0.6, rely=0.1, relwidth=0.3, relheight=0.25)

    select_face_button = SourceButton(
        root,
        text="Select a face",
        cursor="hand2",
        command=lambda: select_source_path(),
        fg_color=("gray75", "gray25"),  # Modern button color
        hover_color=("gray85", "gray35"),
        corner_radius=10,  # Rounded corners
    )
    select_face_button.place(relx=0.1, rely=0.4, relwidth=0.3, relheight=0.1)

    swap_faces_button = ctk.CTkButton(
        root,
        text="↔",
        cursor="hand2",
        command=lambda: swap_faces_paths(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    swap_faces_button.place(relx=0.45, rely=0.4, relwidth=0.1, relheight=0.1)

    select_target_button = TargetButton(
        root,
        text="Select a target",
        cursor="hand2",
        command=lambda: select_target_path(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    select_target_button.place(relx=0.6, rely=0.4, relwidth=0.3, relheight=0.1)

    keep_fps_value = ctk.BooleanVar(value=modules.globals.keep_fps)
    keep_fps_checkbox = ctk.CTkSwitch(
        root,
        text="Keep fps",
        variable=keep_fps_value,
        cursor="hand2",
        command=lambda: setattr(
            modules.globals, "keep_fps", not modules.globals.keep_fps
        ),
        fg_color=("gray75", "gray25"),  # Modern switch color
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    keep_fps_checkbox.place(relx=0.1, rely=0.6)

    keep_frames_value = ctk.BooleanVar(value=modules.globals.keep_frames)
    keep_frames_switch = ctk.CTkSwitch(
        root,
        text="Keep frames",
        variable=keep_frames_value,
        cursor="hand2",
        command=lambda: setattr(
            modules.globals, "keep_frames", keep_frames_value.get()
        ),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    keep_frames_switch.place(relx=0.1, rely=0.65)

    enhancer_value = ctk.BooleanVar(value=modules.globals.fp_ui["face_enhancer"])
    enhancer_switch = ctk.CTkSwitch(
        root,
        text="Face Enhancer",
        variable=enhancer_value,
        cursor="hand2",
        command=lambda: update_tumbler("face_enhancer", enhancer_value.get()),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    enhancer_switch.place(relx=0.1, rely=0.7)

    keep_audio_value = ctk.BooleanVar(value=modules.globals.keep_audio)
    keep_audio_switch = ctk.CTkSwitch(
        root,
        text="Keep audio",
        variable=keep_audio_value,
        cursor="hand2",
        command=lambda: setattr(modules.globals, "keep_audio", keep_audio_value.get()),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    keep_audio_switch.place(relx=0.6, rely=0.6)

    many_faces_value = ctk.BooleanVar(value=modules.globals.many_faces)
    many_faces_switch = ctk.CTkSwitch(
        root,
        text="Many faces",
        variable=many_faces_value,
        cursor="hand2",
        command=lambda: setattr(modules.globals, "many_faces", many_faces_value.get()),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    many_faces_switch.place(relx=0.6, rely=0.65)

    color_correction_value = ctk.BooleanVar(value=modules.globals.color_correction)
    color_correction_switch = ctk.CTkSwitch(
        root,
        text="Fix Blueish Cam -\nforce cv2 to\nuse RGB instead of BGR",
        variable=color_correction_value,
        cursor="hand2",
        command=lambda: setattr(
            modules.globals, "color_correction", color_correction_value.get()
        ),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    color_correction_switch.place(relx=0.6, rely=0.70)

    map_faces = ctk.BooleanVar(value=modules.globals.map_faces)
    map_faces_switch = ctk.CTkSwitch(
        root,
        text="Map faces",
        variable=map_faces,
        cursor="hand2",
        command=lambda: setattr(modules.globals, "map_faces", map_faces.get()),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
    )
    map_faces_switch.place(relx=0.1, rely=0.75)

    start_button = ctk.CTkButton(
        root,
        text="Start",
        cursor="hand2",
        command=lambda: analyze_target(start, root),
        fg_color=("DodgerBlue", "DodgerBlue"),  # Modern button color
        hover_color=("RoyalBlue", "RoyalBlue"),
        corner_radius=10,
    )
    start_button.place(relx=0.15, rely=0.80, relwidth=0.2, relheight=0.05)

    stop_button = ctk.CTkButton(
        root,
        text="Destroy",
        cursor="hand2",
        command=lambda: destroy(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    stop_button.place(relx=0.4, rely=0.80, relwidth=0.2, relheight=0.05)

    preview_button = ctk.CTkButton(
        root,
        text="Preview",
        cursor="hand2",
        command=lambda: toggle_preview(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    preview_button.place(relx=0.65, rely=0.80, relwidth=0.2, relheight=0.05)

    live_button = ctk.CTkButton(
        root,
        text="Live",
        cursor="hand2",
        command=lambda: webcam_preview(root),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    live_button.place(relx=0.40, rely=0.86, relwidth=0.2, relheight=0.05)

    status_label = ctk.CTkLabel(root, text=None, justify="center")
    status_label.place(relx=0.1, rely=0.9, relwidth=0.8)

    donate_label = ctk.CTkLabel(
        root, text="Deep Live Cam", justify="center", cursor="hand2"
    )
    donate_label.place(relx=0.1, rely=0.95, relwidth=0.8)

    # Access the URL text color directly
    donate_label.configure(text_color="dodger blue")

    donate_label.bind(
        "<Button>", lambda event: webbrowser.open("https://paypal.me/hacksider")
    )

    return root


def analyze_target(start: Callable[[], None], root: ctk.CTk):
    if POPUP != None and POPUP.winfo_exists():
        update_status("Please complete pop-up or close it.")
        return

    if modules.globals.map_faces:
        modules.globals.souce_target_map = []

        if is_image(modules.globals.target_path):
            update_status("Getting unique faces")
            get_unique_faces_from_target_image()
        elif is_video(modules.globals.target_path):
            update_status("Getting unique faces")
            get_unique_faces_from_target_video()

        if len(modules.globals.souce_target_map) > 0:
            create_source_target_popup(start, root, modules.globals.souce_target_map)
        else:
            update_status("No faces found in target")
    else:
        select_output_path(start)


def create_source_target_popup(
    start: Callable[[], None], root: ctk.CTk, map: list
) -> None:
    global POPUP, popup_status_label

    POPUP = ctk.CTkToplevel(root)
    POPUP.title("Source x Target Mapper")
    POPUP.geometry(f"{POPUP_WIDTH}x{POPUP_HEIGHT}")
    POPUP.focus()

    def on_submit_click(start):
        if has_valid_map():
            POPUP.destroy()
            select_output_path(start)
        else:
            update_pop_status("Atleast 1 source with target is required!")

    scrollable_frame = ctk.CTkScrollableFrame(
        POPUP, width=POPUP_SCROLL_WIDTH, height=POPUP_SCROLL_HEIGHT
    )
    scrollable_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

    def on_button_click(map, button_num):
        update_popup_source(scrollable_frame, map, button_num)

    for item in map:
        id = item["id"]

        button = SourceMapperButton(
            scrollable_frame,
            map,
            id,
            text="Select source image",
            command=lambda id=id: on_button_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )
        button.grid(row=id, column=0, padx=50, pady=10)

        x_label = ctk.CTkLabel(
            scrollable_frame,
            text=f"X",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
        )
        x_label.grid(row=id, column=2, padx=10, pady=10)

        image = Image.fromarray(cv2.cvtColor(item["target"]["cv2"], cv2.COLOR_BGR2RGB))
        image = image.resize(
            (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
        )
        tk_image = ctk.CTkImage(image, size=image.size)

        target_image = ctk.CTkLabel(
            scrollable_frame,
            text=f"T-{id}",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
        )
        target_image.grid(row=id, column=3, padx=10, pady=10)
        target_image.configure(image=tk_image)

    popup_status_label = ctk.CTkLabel(POPUP, text=None, justify="center")
    popup_status_label.grid(row=1, column=0, pady=15)

    close_button = ctk.CTkButton(
        POPUP,
        text="Submit",
        command=lambda: on_submit_click(start),
        fg_color=("DodgerBlue", "DodgerBlue"),
        hover_color=("RoyalBlue", "RoyalBlue"),
        corner_radius=10,
    )
    close_button.grid(row=2, column=0, pady=10)


def update_popup_source(
    scrollable_frame: ctk.CTkScrollableFrame,
    map: list,
    button_num: int,
    source_path: str = None,
) -> list:
    global source_label_dict, RECENT_DIRECTORY_SOURCE

    if source_path is None:
        source_path = ctk.filedialog.askopenfilename(
            title="select an source image",
            initialdir=RECENT_DIRECTORY_SOURCE,
            filetypes=[img_ft],
        )

    if "source" in map[button_num]:
        map[button_num].pop("source")
        source_label_dict[button_num].destroy()
        del source_label_dict[button_num]

    if source_path == "":
        return map
    else:
        RECENT_DIRECTORY_SOURCE = os.path.dirname(source_path)
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["source"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            source_image = ctk.CTkLabel(
                scrollable_frame,
                text=f"S-{button_num}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
            )
            source_image.grid(row=button_num, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)
            source_label_dict[button_num] = source_image
        else:
            update_pop_status("Face could not be detected in last upload!")
        return map


def create_preview(parent: ctk.CTkToplevel) -> ctk.CTkToplevel:
    global preview_label, preview_slider

    preview = ctk.CTkToplevel(parent)
    preview.withdraw()
    preview.title("Preview")
    preview.configure()
    preview.protocol("WM_DELETE_WINDOW", lambda: toggle_preview())
    preview.resizable(width=True, height=True)

    preview_label = ctk.CTkLabel(preview, text=None)
    preview_label.pack(fill="both", expand=True)

    preview_slider = ctk.CTkSlider(
        preview,
        from_=0,
        to=0,
        command=lambda frame_value: update_preview(frame_value),
        fg_color=("gray75", "gray25"),
        progress_color=("DodgerBlue", "DodgerBlue"),
        button_color=("DodgerBlue", "DodgerBlue"),
        button_hover_color=("RoyalBlue", "RoyalBlue"),
    )

    return preview


def update_status(text: str) -> None:
    status_label.configure(text=text)
    ROOT.update()


def update_pop_status(text: str) -> None:
    popup_status_label.configure(text=text)


def update_pop_live_status(text: str) -> None:
    popup_status_label_live.configure(text=text)


def update_tumbler(var: str, value: bool) -> None:
    modules.globals.fp_ui[var] = value


def select_source_path() -> None:
    global RECENT_DIRECTORY_SOURCE, img_ft, vid_ft

    PREVIEW.withdraw()
    source_path = ctk.filedialog.askopenfilename(
        title="select an source image",
        initialdir=RECENT_DIRECTORY_SOURCE,
        filetypes=[img_ft],
    )
    if is_image(source_path):
        modules.globals.source_path = source_path
        RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
        image = render_image_preview(modules.globals.source_path, (200, 200))
        source_label.configure(image=image)
        source_label.configure(text="")
    else:
        modules.globals.source_path = None
        source_label.configure(image=None)
        source_label.configure(text="Drag & Drop Source Image Here")


def swap_faces_paths() -> None:
    global RECENT_DIRECTORY_SOURCE, RECENT_DIRECTORY_TARGET

    source_path = modules.globals.source_path
    target_path = modules.globals.target_path

    if not is_image(source_path) or not is_image(target_path):
        return

    modules.globals.source_path = target_path
    modules.globals.target_path = source_path

    RECENT_DIRECTORY_SOURCE = os.path.dirname(modules.globals.source_path)
    RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)

    PREVIEW.withdraw()

    source_image = render_image_preview(modules.globals.source_path, (200, 200))
    source_label.configure(image=source_image)
    source_label.configure(text="")

    target_image = render_image_preview(modules.globals.target_path, (200, 200))
    target_label.configure(image=target_image)
    target_label.configure(text="")


def select_target_path() -> None:
    global RECENT_DIRECTORY_TARGET, img_ft, vid_ft

    PREVIEW.withdraw()
    target_path = ctk.filedialog.askopenfilename(
        title="select an target image or video",
        initialdir=RECENT_DIRECTORY_TARGET,
        filetypes=[img_ft, vid_ft],
    )
    if is_image(target_path):
        modules.globals.target_path = target_path
        RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
        image = render_image_preview(modules.globals.target_path, (200, 200))
        target_label.configure(image=image)
        target_label.configure(text="")
    elif is_video(target_path):
        modules.globals.target_path = target_path
        RECENT_DIRECTORY_TARGET = os.path.dirname(modules.globals.target_path)
        video_frame = render_video_preview(target_path, (200, 200))
        target_label.configure(image=video_frame)
        target_label.configure(text="")
    else:
        modules.globals.target_path = None
        target_label.configure(image=None)
        target_label.configure(text="Drag & Drop Target Image/Video Here")


def select_output_path(start: Callable[[], None]) -> None:
    global RECENT_DIRECTORY_OUTPUT, img_ft, vid_ft

    if is_image(modules.globals.target_path):
        output_path = ctk.filedialog.asksaveasfilename(
            title="save image output file",
            filetypes=[img_ft],
            defaultextension=".png",
            initialfile="output.png",
            initialdir=RECENT_DIRECTORY_OUTPUT,
        )
    elif is_video(modules.globals.target_path):
        output_path = ctk.filedialog.asksaveasfilename(
            title="save video output file",
            filetypes=[vid_ft],
            defaultextension=".mp4",
            initialfile="output.mp4",
            initialdir=RECENT_DIRECTORY_OUTPUT,
        )
    else:
        output_path = None
    if output_path:
        modules.globals.output_path = output_path
        RECENT_DIRECTORY_OUTPUT = os.path.dirname(modules.globals.output_path)
        start()


def check_and_ignore_nsfw(target, destroy: Callable = None) -> bool:
    """Check if the target is NSFW.
    TODO: Consider to make blur the target.
    """
    from numpy import ndarray
    from modules.predicter import predict_image, predict_video, predict_frame

    if type(target) is str:  # image/video file path
        check_nsfw = predict_image if has_image_extension(target) else predict_video
    elif type(target) is ndarray:  # frame object
        check_nsfw = predict_frame
    if check_nsfw and check_nsfw(target):
        if destroy:
            destroy(
                to_quit=False
            )  # Do not need to destroy the window frame if the target is NSFW
        update_status("Processing ignored!")
        return True
    else:
        return False


def fit_image_to_size(image, width: int, height: int):
    if width is None and height is None:
        return image
    h, w, _ = image.shape
    ratio_h = 0.0
    ratio_w = 0.0
    if width > height:
        ratio_h = height / h
    else:
        ratio_w = width / w
    ratio = max(ratio_w, ratio_h)
    new_size = (int(ratio * w), int(ratio * h))
    return cv2.resize(image, dsize=new_size)


def render_image_preview(image_path: str, size: Tuple[int, int]) -> ctk.CTkImage:
    image = Image.open(image_path)
    if size:
        image = ImageOps.fit(image, size, Image.LANCZOS)
    return ctk.CTkImage(image, size=image.size)


def render_video_preview(
    video_path: str, size: Tuple[int, int], frame_number: int = 0
) -> ctk.CTkImage:
    capture = cv2.VideoCapture(video_path)
    if frame_number:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    has_frame, frame = capture.read()
    if has_frame:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if size:
            image = ImageOps.fit(image, size, Image.LANCZOS)
        return ctk.CTkImage(image, size=image.size)
    capture.release()
    cv2.destroyAllWindows()


def toggle_preview() -> None:
    if PREVIEW.state() == "normal":
        PREVIEW.withdraw()
    elif modules.globals.source_path and modules.globals.target_path:
        init_preview()
        update_preview()


def init_preview() -> None:
    if is_image(modules.globals.target_path):
        preview_slider.pack_forget()
    if is_video(modules.globals.target_path):
        video_frame_total = get_video_frame_total(modules.globals.target_path)
        preview_slider.configure(to=video_frame_total)
        preview_slider.pack(fill="x")
        preview_slider.set(0)


def update_preview(frame_number: int = 0) -> None:
    if modules.globals.source_path and modules.globals.target_path:
        update_status("Processing...")
        temp_frame = get_video_frame(modules.globals.target_path, frame_number)
        if modules.globals.nsfw_filter and check_and_ignore_nsfw(temp_frame):
            return
        for frame_processor in get_frame_processors_modules(
            modules.globals.frame_processors
        ):
            temp_frame = frame_processor.process_frame(
                get_one_face(cv2.imread(modules.globals.source_path)), temp_frame
            )
        image = Image.fromarray(cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB))
        image = ImageOps.contain(
            image, (PREVIEW_MAX_WIDTH, PREVIEW_MAX_HEIGHT), Image.LANCZOS
        )
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        update_status("Processing succeed!")
        PREVIEW.deiconify()


def webcam_preview(root: ctk.CTk):
    if not modules.globals.map_faces:
        if modules.globals.source_path is None:
            # No image selected
            return
        create_webcam_preview()
    else:
        modules.globals.souce_target_map = []
        create_source_target_popup_for_webcam(root, modules.globals.souce_target_map)


def create_webcam_preview():
    global preview_label, PREVIEW

    camera = cv2.VideoCapture(
        0
    )  # Use index for the webcam (adjust the index accordingly if necessary)
    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH, PREVIEW_DEFAULT_WIDTH
    )  # Set the width of the resolution
    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT, PREVIEW_DEFAULT_HEIGHT
    )  # Set the height of the resolution
    camera.set(cv2.CAP_PROP_FPS, 60)  # Set the frame rate of the webcam

    preview_label.configure(
        width=PREVIEW_DEFAULT_WIDTH, height=PREVIEW_DEFAULT_HEIGHT
    )  # Reset the preview image before startup

    PREVIEW.deiconify()  # Open preview window

    frame_processors = get_frame_processors_modules(modules.globals.frame_processors)

    source_image = None  # Initialize variable for the selected face image

    while camera:
        ret, frame = camera.read()
        if not ret:
            break

        temp_frame = frame.copy()  # Create a copy of the frame

        if modules.globals.live_mirror:
            temp_frame = cv2.flip(temp_frame, 1)  # horizontal flipping

        if modules.globals.live_resizable:
            temp_frame = fit_image_to_size(
                temp_frame, PREVIEW.winfo_width(), PREVIEW.winfo_height()
            )

        if not modules.globals.map_faces:
            # Select and save face image only once
            if source_image is None and modules.globals.source_path:
                source_image = get_one_face(cv2.imread(modules.globals.source_path))

            for frame_processor in frame_processors:
                temp_frame = frame_processor.process_frame(source_image, temp_frame)
        else:
            modules.globals.target_path = None

            for frame_processor in frame_processors:
                temp_frame = frame_processor.process_frame_v2(temp_frame)

        image = cv2.cvtColor(
            temp_frame, cv2.COLOR_BGR2RGB
        )  # Convert the image to RGB format to display it with Tkinter
        image = Image.fromarray(image)
        image = ImageOps.contain(
            image, (temp_frame.shape[1], temp_frame.shape[0]), Image.LANCZOS
        )
        image = ctk.CTkImage(image, size=image.size)
        preview_label.configure(image=image)
        ROOT.update()

        if PREVIEW.state() == "withdrawn":
            break

    camera.release()
    PREVIEW.withdraw()  # Close preview window when loop is finished


def create_source_target_popup_for_webcam(root: ctk.CTk, map: list) -> None:
    global POPUP_LIVE, popup_status_label_live

    POPUP_LIVE = ctk.CTkToplevel(root)
    POPUP_LIVE.title("Source x Target Mapper")
    POPUP_LIVE.geometry(f"{POPUP_LIVE_WIDTH}x{POPUP_LIVE_HEIGHT}")
    POPUP_LIVE.focus()

    def on_submit_click():
        if has_valid_map():
            POPUP_LIVE.destroy()
            simplify_maps()
            create_webcam_preview()
        else:
            update_pop_live_status("Atleast 1 source with target is required!")

    def on_add_click():
        add_blank_map()
        refresh_data(map)
        update_pop_live_status("Please provide mapping!")

    popup_status_label_live = ctk.CTkLabel(POPUP_LIVE, text=None, justify="center")
    popup_status_label_live.grid(row=1, column=0, pady=15)

    add_button = ctk.CTkButton(
        POPUP_LIVE,
        text="Add",
        command=lambda: on_add_click(),
        fg_color=("gray75", "gray25"),
        hover_color=("gray85", "gray35"),
        corner_radius=10,
    )
    add_button.place(relx=0.2, rely=0.92, relwidth=0.2, relheight=0.05)

    close_button = ctk.CTkButton(
        POPUP_LIVE,
        text="Submit",
        command=lambda: on_submit_click(),
        fg_color=("DodgerBlue", "DodgerBlue"),
        hover_color=("RoyalBlue", "RoyalBlue"),
        corner_radius=10,
    )
    close_button.place(relx=0.6, rely=0.92, relwidth=0.2, relheight=0.05)

    refresh_data(map)  # Initial data refresh


def refresh_data(map: list):
    global POPUP_LIVE

    # Destroy existing widgets in the scrollable frame
    for widget in POPUP_LIVE.winfo_children():
        if isinstance(widget, ctk.CTkScrollableFrame):
            widget.destroy()

    scrollable_frame = ctk.CTkScrollableFrame(
        POPUP_LIVE, width=POPUP_LIVE_SCROLL_WIDTH, height=POPUP_LIVE_SCROLL_HEIGHT
    )
    scrollable_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

    def on_sbutton_click(map, button_num):
        map = update_webcam_source(scrollable_frame, map, button_num)

    def on_tbutton_click(map, button_num):
        map = update_webcam_target(scrollable_frame, map, button_num)

    for item in map:
        id = item["id"]

        button = ctk.CTkButton(
            scrollable_frame,
            text="Select source image",
            command=lambda id=id: on_sbutton_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )
        button.grid(row=id, column=0, padx=30, pady=10)

        x_label = ctk.CTkLabel(
            scrollable_frame,
            text=f"X",
            width=MAPPER_PREVIEW_MAX_WIDTH,
            height=MAPPER_PREVIEW_MAX_HEIGHT,
        )
        x_label.grid(row=id, column=2, padx=10, pady=10)

        button = ctk.CTkButton(
            scrollable_frame,
            text="Select target image",
            command=lambda id=id: on_tbutton_click(map, id),
            width=DEFAULT_BUTTON_WIDTH,
            height=DEFAULT_BUTTON_HEIGHT,
            fg_color=("gray75", "gray25"),
            hover_color=("gray85", "gray35"),
            corner_radius=10,
        )
        button.grid(row=id, column=3, padx=20, pady=10)

        if "source" in item:
            image = Image.fromarray(
                cv2.cvtColor(item["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            source_image = ctk.CTkLabel(
                scrollable_frame,
                text=f"S-{id}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
            )
            source_image.grid(row=id, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)

        if "target" in item:
            image = Image.fromarray(
                cv2.cvtColor(item["target"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            target_image = ctk.CTkLabel(
                scrollable_frame,
                text=f"T-{id}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
            )
            target_image.grid(row=id, column=4, padx=20, pady=10)
            target_image.configure(image=tk_image)


def update_webcam_source(
    scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int
) -> list:
    global source_label_dict_live

    source_path = ctk.filedialog.askopenfilename(
        title="select an source image",
        initialdir=RECENT_DIRECTORY_SOURCE,
        filetypes=[img_ft],
    )

    if "source" in map[button_num]:
        map[button_num].pop("source")
        if button_num in source_label_dict_live:
            source_label_dict_live[button_num].destroy()
            del source_label_dict_live[button_num]

    if source_path == "":
        return map
    else:
        cv2_img = cv2.imread(source_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["source"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["source"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            source_image = ctk.CTkLabel(
                scrollable_frame,
                text=f"S-{button_num}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
            )
            source_image.grid(row=button_num, column=1, padx=10, pady=10)
            source_image.configure(image=tk_image)
            source_label_dict_live[button_num] = source_image
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map


def update_webcam_target(
    scrollable_frame: ctk.CTkScrollableFrame, map: list, button_num: int
) -> list:
    global target_label_dict_live

    target_path = ctk.filedialog.askopenfilename(
        title="select an target image",
        initialdir=RECENT_DIRECTORY_SOURCE,
        filetypes=[img_ft],
    )

    if "target" in map[button_num]:
        map[button_num].pop("target")
        if button_num in target_label_dict_live:
            target_label_dict_live[button_num].destroy()
            del target_label_dict_live[button_num]

    if target_path == "":
        return map
    else:
        cv2_img = cv2.imread(target_path)
        face = get_one_face(cv2_img)

        if face:
            x_min, y_min, x_max, y_max = face["bbox"]

            map[button_num]["target"] = {
                "cv2": cv2_img[int(y_min) : int(y_max), int(x_min) : int(x_max)],
                "face": face,
            }

            image = Image.fromarray(
                cv2.cvtColor(map[button_num]["target"]["cv2"], cv2.COLOR_BGR2RGB)
            )
            image = image.resize(
                (MAPPER_PREVIEW_MAX_WIDTH, MAPPER_PREVIEW_MAX_HEIGHT), Image.LANCZOS
            )
            tk_image = ctk.CTkImage(image, size=image.size)

            target_image = ctk.CTkLabel(
                scrollable_frame,
                text=f"T-{button_num}",
                width=MAPPER_PREVIEW_MAX_WIDTH,
                height=MAPPER_PREVIEW_MAX_HEIGHT,
            )
            target_image.grid(row=button_num, column=4, padx=20, pady=10)
            target_image.configure(image=tk_image)
            target_label_dict_live[button_num] = target_image
        else:
            update_pop_live_status("Face could not be detected in last upload!")
        return map
