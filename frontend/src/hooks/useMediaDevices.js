import { useCallback, useState } from "react";

/**
 * On-demand microphone and camera verification hook for the studio DeviceCheck panel.
 * Requests device access only when explicitly triggered by the user and immediately
 * releases test media tracks once verified.
 */
export function useMediaDevices() {
  const [micStatus, setMicStatus] = useState("idle"); // idle | checking | ready | denied | unavailable
  const [cameraStatus, setCameraStatus] = useState("idle"); // idle | checking | ready | denied | unavailable
  const [deviceError, setDeviceError] = useState("");

  const checkMicrophone = useCallback(async () => {
    setDeviceError("");
    if (!navigator?.mediaDevices?.getUserMedia) {
      setMicStatus("unavailable");
      setDeviceError("Audio capture is not available in this browser.");
      return false;
    }

    setMicStatus("checking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore
        }
      });
      setMicStatus("ready");
      return true;
    } catch (err) {
      const isDenied =
        err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError";
      setMicStatus(isDenied ? "denied" : "unavailable");
      setDeviceError(
        isDenied
          ? "Microphone permission was denied. Allow access in your browser settings to record voice answers."
          : "No working microphone was detected."
      );
      return false;
    }
  }, []);

  const checkCamera = useCallback(async () => {
    setDeviceError("");
    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraStatus("unavailable");
      setDeviceError("Camera access is not available in this browser.");
      return false;
    }

    setCameraStatus("checking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {
          // Ignore
        }
      });
      setCameraStatus("ready");
      return true;
    } catch (err) {
      const isDenied =
        err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError";
      setCameraStatus(isDenied ? "denied" : "unavailable");
      setDeviceError(
        isDenied
          ? "Camera permission was denied. Allow access in your browser settings if you want video feedback."
          : "No working camera was detected."
      );
      return false;
    }
  }, []);

  return {
    micStatus,
    cameraStatus,
    deviceError,
    checkMicrophone,
    checkCamera,
  };
}

