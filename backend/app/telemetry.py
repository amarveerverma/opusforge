"""
ClipForge Hardware Telemetry Engine
Monitors GPU VRAM, Temperature, Utilization, System RAM, and Disk space.
"""
import shutil
import psutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger("clipforge.telemetry")

# Try initializing NVML
_NVML_INITIALIZED = False
try:
    try:
        import nvidia_ml_py as pynvml
    except ImportError:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            import pynvml
    pynvml.nvmlInit()
    _NVML_INITIALIZED = True
except Exception as e:
    logger.warning("NVML initialization warning: %s", e)

def get_gpu_telemetry() -> Dict[str, Any]:
    """Retrieves real-time GPU hardware metrics."""
    if not _NVML_INITIALIZED:
        return {
            "name": "N/A (CPU Mode)",
            "available": False,
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "utilization_percent": 0,
            "temperature_c": 0,
        }
    
    try:
        try:
            import nvidia_ml_py as pynvml
        except ImportError:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=FutureWarning)
                import pynvml
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
        except Exception:
            util = 0
            
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except Exception:
            temp = 0
            
        total_mb = int(mem.total // (1024 * 1024))
        free_mb = int(mem.free // (1024 * 1024))
        used_mb = int(mem.used // (1024 * 1024))
        
        return {
            "name": name,
            "available": True,
            "vram_total_mb": total_mb,
            "vram_used_mb": used_mb,
            "vram_free_mb": free_mb,
            "utilization_percent": util,
            "temperature_c": temp,
        }
    except Exception as e:
        logger.error("Failed to query GPU telemetry: %s", e)
        return {
            "name": "Error querying GPU",
            "available": False,
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "utilization_percent": 0,
            "temperature_c": 0,
            "error": str(e),
        }

def get_ram_telemetry() -> Dict[str, Any]:
    """Retrieves real-time system RAM metrics."""
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "percent": mem.percent,
        }
    except Exception as e:
        return {"error": str(e)}

def get_disk_telemetry(path: str = "C:\\") -> Dict[str, Any]:
    """Retrieves storage metrics for the drive containing ClipForge."""
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent_free": round((usage.free / usage.total) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}

def get_available_encoders() -> List[str]:
    """List supported hardware and software video encoders."""
    return ["h264_nvenc", "hevc_nvenc", "av1_nvenc", "libx264"]

def get_full_system_status() -> Dict[str, Any]:
    """Consolidated telemetry snapshot for the dashboard."""
    return {
        "status": "online",
        "gpu": get_gpu_telemetry(),
        "ram": get_ram_telemetry(),
        "disk": get_disk_telemetry(),
        "encoders": get_available_encoders(),
    }
