"""Blend Autosave Cleaner - delete old autosave .blend files from the temp folder."""

import os
import platform
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import bpy
from bpy.props import BoolProperty, IntProperty
from bpy.types import AddonPreferences, Operator

try:
    from send2trash import send2trash as _send2trash
except ImportError:
    _send2trash = None


ADDON_ID = __package__
LOG_FILENAME = "blend_autosave_cleaner.log"
LOG_MAX_LINES = 100
SECONDS_PER_DAY = 86400.0


def _resolve_temp_dir() -> Path:
    pref_path = bpy.context.preferences.filepaths.temporary_directory
    if pref_path and os.path.isdir(pref_path):
        return Path(pref_path)
    return Path(tempfile.gettempdir())


def _get_prefs():
    return bpy.context.preferences.addons[ADDON_ID].preferences


def _is_target(path: Path, prefs) -> bool:
    name = path.name.lower()
    if name == "quit.blend":
        return prefs.target_quit
    suffix = path.suffix.lower()
    if suffix == ".blend":
        return prefs.target_blend
    if suffix == ".blend1":
        return prefs.target_blend1
    if suffix == ".blend2":
        return prefs.target_blend2
    return False


def _format_size(n_bytes: int) -> str:
    size = float(n_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _t(msg: str) -> str:
    return bpy.app.translations.pgettext(msg)


def _format_report(stats: dict) -> str:
    if stats.get("disabled"):
        return _t("Cleanup disabled (retention=0)")
    parts = [_t("Deleted {n} file(s) ({size})").format(
        n=stats["deleted"], size=_format_size(stats["freed_bytes"])
    )]
    if stats.get("dry_run"):
        parts.append(_t("dry run"))
    if stats.get("errors"):
        parts.append(_t("{n} error(s)").format(n=len(stats["errors"])))
    return ", ".join(parts)


def _cleanup(prefs) -> dict:
    temp_dir = _resolve_temp_dir()
    stats = {
        "deleted": 0,
        "freed_bytes": 0,
        "errors": [],
        "temp_dir": str(temp_dir),
        "dry_run": bool(prefs.dry_run),
        "disabled": False,
    }
    if prefs.retention_days <= 0:
        stats["disabled"] = True
        return stats
    if not temp_dir.exists():
        return stats

    cutoff = time.time() - float(prefs.retention_days) * SECONDS_PER_DAY

    for entry in temp_dir.iterdir():
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        if not _is_target(entry, prefs):
            continue
        try:
            st = entry.stat()
        except OSError as e:
            stats["errors"].append(f"stat: {entry.name}: {e}")
            continue
        if st.st_mtime > cutoff:
            continue
        if prefs.dry_run:
            stats["deleted"] += 1
            stats["freed_bytes"] += st.st_size
            continue
        try:
            if prefs.use_recycle_bin and _send2trash is not None:
                _send2trash(str(entry))
            else:
                entry.unlink()
            stats["deleted"] += 1
            stats["freed_bytes"] += st.st_size
        except OSError as e:
            stats["errors"].append(f"delete: {entry.name}: {e}")
        except Exception as e:
            stats["errors"].append(f"trash: {entry.name}: {e}")

    return stats


def _write_log(stats: dict) -> None:
    try:
        prefs = _get_prefs()
    except (KeyError, AttributeError):
        return
    if not prefs.enable_log:
        return
    log_path = _resolve_temp_dir() / LOG_FILENAME
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{timestamp}] deleted={stats['deleted']} "
        f"freed={stats['freed_bytes']} dry_run={stats['dry_run']}"
    )
    if stats["errors"]:
        line += f" errors={len(stats['errors'])}"

    try:
        existing: list[str] = []
        if log_path.exists():
            existing = log_path.read_text(encoding="utf-8").splitlines()
        existing.append(line)
        existing = existing[-LOG_MAX_LINES:]
        log_path.write_text("\n".join(existing) + "\n", encoding="utf-8")
    except OSError:
        pass


class BAC_OT_clean_now(Operator):
    bl_idname = "blend_autosave_cleaner.clean_now"
    bl_label = "Clean Now"
    bl_description = "Delete old autosave files now"

    def execute(self, context):
        prefs = _get_prefs()
        stats = _cleanup(prefs)
        _write_log(stats)
        msg = _format_report(stats)
        level = {"ERROR"} if stats["errors"] else {"INFO"}
        self.report(level, msg)
        return {"FINISHED"}

    def invoke(self, context, event):
        prefs = _get_prefs()
        if prefs.confirm_before_delete and not prefs.dry_run:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)


class BAC_OT_open_temp_folder(Operator):
    bl_idname = "blend_autosave_cleaner.open_temp_folder"
    bl_label = "Open Temp Folder"
    bl_description = "Open the temporary folder in the OS file manager"

    def execute(self, context):
        path = str(_resolve_temp_dir())
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as e:
            self.report({"ERROR"}, f"Failed to open: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class BAC_AddonPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    retention_days: IntProperty(
        name="Retention Days",
        description="Files older than this many days are deleted (0 = disabled)",
        default=7,
        min=0,
        max=365,
    )

    target_blend: BoolProperty(name=".blend", default=True)
    target_blend1: BoolProperty(name=".blend1", default=True)
    target_blend2: BoolProperty(name=".blend2", default=True)
    target_quit: BoolProperty(name="quit.blend", default=True)

    use_recycle_bin: BoolProperty(
        name="Send to Recycle Bin",
        description="Move files to the OS recycle bin instead of deleting permanently",
        default=True,
    )
    run_on_startup: BoolProperty(
        name="Run on Blender startup",
        description="Automatically clean when Blender starts",
        default=True,
    )
    confirm_before_delete: BoolProperty(
        name="Confirm before deletion",
        description="Show a confirmation dialog before deleting",
        default=False,
    )
    dry_run: BoolProperty(
        name="Dry Run",
        description="Log what would be deleted without actually deleting",
        default=True,
    )
    enable_log: BoolProperty(
        name="Enable log file",
        description=f"Append a record of each run to {LOG_FILENAME}",
        default=True,
    )

    def draw(self, context):
        layout = self.layout

        layout.label(
            text=f"{_t('Target folder')}: {_resolve_temp_dir()}",
            icon="FILE_FOLDER",
        )

        layout.prop(self, "retention_days")

        box = layout.box()
        box.label(text="Target file types")
        row = box.row(align=True)
        row.prop(self, "target_blend")
        row.prop(self, "target_blend1")
        row.prop(self, "target_blend2")
        row.prop(self, "target_quit")

        box = layout.box()
        box.label(text="Behavior")
        box.prop(self, "use_recycle_bin")
        box.prop(self, "run_on_startup")
        box.prop(self, "confirm_before_delete")
        box.prop(self, "dry_run")
        box.prop(self, "enable_log")

        row = layout.row(align=True)
        row.operator(BAC_OT_clean_now.bl_idname, icon="TRASH")
        row.operator(BAC_OT_open_temp_folder.bl_idname, icon="FILE_FOLDER")


classes = (
    BAC_AddonPreferences,
    BAC_OT_clean_now,
    BAC_OT_open_temp_folder,
)


TRANSLATIONS = {
    "ja_JP": {
        # Property names / descriptions
        ("*", "Retention Days"): "保持日数",
        ("*", "Files older than this many days are deleted (0 = disabled)"):
            "この日数より古いファイルを削除（0 で無効）",
        ("*", "Send to Recycle Bin"): "ごみ箱に送る",
        ("*", "Move files to the OS recycle bin instead of deleting permanently"):
            "完全削除せず OS のごみ箱に送る",
        ("*", "Run on Blender startup"): "Blender 起動時に実行",
        ("*", "Automatically clean when Blender starts"):
            "Blender 起動時に自動でクリーンアップ",
        ("*", "Confirm before deletion"): "削除前に確認",
        ("*", "Show a confirmation dialog before deleting"):
            "削除前に確認ダイアログを表示",
        ("*", "Dry Run"): "ドライラン",
        ("*", "Log what would be deleted without actually deleting"):
            "実際には削除せずログのみ記録",
        ("*", "Enable log file"): "ログファイルを有効化",
        ("*", f"Append a record of each run to {LOG_FILENAME}"):
            f"実行ログを {LOG_FILENAME} に追記",
        # UI labels
        ("*", "Target folder"): "対象フォルダ",
        ("*", "Target file types"): "対象ファイル種別",
        ("*", "Behavior"): "動作",
        # Operator labels (registered under both contexts to be safe)
        ("*", "Clean Now"): "今すぐクリーンアップ",
        ("Operator", "Clean Now"): "今すぐクリーンアップ",
        ("*", "Delete old autosave files now"):
            "古い自動保存ファイルを今すぐ削除",
        ("*", "Open Temp Folder"): "Temp フォルダを開く",
        ("Operator", "Open Temp Folder"): "Temp フォルダを開く",
        ("*", "Open the temporary folder in the OS file manager"):
            "OS のファイルマネージャで Temp フォルダを開く",
        # Report messages (formatted via pgettext)
        ("*", "Deleted {n} file(s) ({size})"):
            "{n} 個のファイルを削除（{size}）",
        ("*", "dry run"): "ドライラン",
        ("*", "{n} error(s)"): "{n} 件のエラー",
        ("*", "Cleanup disabled (retention=0)"):
            "クリーンアップ無効（保持日数 = 0）",
    }
}


def _startup_run():
    try:
        prefs = _get_prefs()
    except (KeyError, AttributeError):
        return None
    if not prefs.run_on_startup:
        return None
    try:
        stats = _cleanup(prefs)
        _write_log(stats)
        print(f"[blend_autosave_cleaner] startup: {_format_report(stats)}")
    except Exception as e:
        print(f"[blend_autosave_cleaner] startup cleanup failed: {e}")
    return None


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.translations.register(__package__, TRANSLATIONS)
    bpy.app.timers.register(_startup_run, first_interval=2.0)


def unregister():
    if bpy.app.timers.is_registered(_startup_run):
        bpy.app.timers.unregister(_startup_run)
    bpy.app.translations.unregister(__package__)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
