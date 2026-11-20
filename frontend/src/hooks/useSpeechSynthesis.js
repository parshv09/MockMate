import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Browser SpeechSynthesis hook for reading interview questions aloud.
 * - Prevents overlapping speech by always cancelling active utterances first.
 * - Synchronizes isSpeaking and isPaused states with utterance lifecycle events.
 * - Cancels active speech automatically on unmount.
 * - Degrades gracefully when window.speechSynthesis is unavailable.
 */
export function useSpeechSynthesis() {
  const isSupported =
    typeof window !== "undefined" &&
    "speechSynthesis" in window &&
    typeof window.SpeechSynthesisUtterance !== "undefined";

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolumeState] = useState(1);
  const [voices, setVoices] = useState([]);
  const [selectedVoiceURI, setSelectedVoiceURI] = useState("");

  const utteranceRef = useRef(null);
  const lastSpokenTextRef = useRef("");

  useEffect(() => {
    if (!isSupported) return undefined;

    function loadVoices() {
      try {
        const available = window.speechSynthesis.getVoices() || [];
        setVoices(available);
        if (available.length > 0) {
          setSelectedVoiceURI((prev) => {
            if (prev && available.some((v) => v.voiceURI === prev)) {
              return prev;
            }
            const englishVoice = available.find((v) =>
              String(v.lang || "").toLowerCase().startsWith("en")
            );
            return (englishVoice || available[0]).voiceURI;
          });
        }
      } catch {
        setVoices([]);
      }
    }

    loadVoices();
    const synth = window.speechSynthesis;
    if (synth && "onvoiceschanged" in synth) {
      synth.onvoiceschanged = loadVoices;
    }

    return () => {
      if (synth && "onvoiceschanged" in synth) {
        synth.onvoiceschanged = null;
      }
    };
  }, [isSupported]);

  const stop = useCallback(() => {
    if (!isSupported) return;
    try {
      window.speechSynthesis.cancel();
    } catch {
      // Ignore speechSynthesis cancel errors cleanly
    }
    utteranceRef.current = null;
    setIsSpeaking(false);
    setIsPaused(false);
  }, [isSupported]);

  const speak = useCallback(
    (text) => {
      const cleaned = (text || "").trim();
      lastSpokenTextRef.current = cleaned;

      if (!isSupported || !cleaned) {
        return false;
      }

      // Always cancel any existing speech first to prevent overlap
      try {
        window.speechSynthesis.cancel();
      } catch {
        // Ignore cancel errors
      }

      if (isMuted) {
        setIsSpeaking(false);
        setIsPaused(false);
        return false;
      }

      try {
        const utterance = new window.SpeechSynthesisUtterance(cleaned);
        utterance.volume = Math.min(1, Math.max(0, Number(volume) ?? 1));

        if (selectedVoiceURI && voices.length > 0) {
          const matchedVoice = voices.find((v) => v.voiceURI === selectedVoiceURI);
          if (matchedVoice) {
            utterance.voice = matchedVoice;
          }
        }

        utterance.onstart = () => {
          setIsSpeaking(true);
          setIsPaused(false);
        };
        utterance.onpause = () => {
          setIsPaused(true);
        };
        utterance.onresume = () => {
          setIsPaused(false);
          setIsSpeaking(true);
        };
        utterance.onend = () => {
          setIsSpeaking(false);
          setIsPaused(false);
        };
        utterance.onerror = () => {
          setIsSpeaking(false);
          setIsPaused(false);
        };

        utteranceRef.current = utterance;
        setIsSpeaking(true);
        setIsPaused(false);
        window.speechSynthesis.speak(utterance);
        return true;
      } catch {
        setIsSpeaking(false);
        setIsPaused(false);
        return false;
      }
    },
    [isSupported, isMuted, volume, selectedVoiceURI, voices]
  );

  const pause = useCallback(() => {
    if (!isSupported || !isSpeaking || isPaused) return;
    try {
      window.speechSynthesis.pause();
      setIsPaused(true);
    } catch {
      // Ignore pause errors
    }
  }, [isSupported, isSpeaking, isPaused]);

  const resume = useCallback(() => {
    if (!isSupported || !isPaused) return;
    try {
      window.speechSynthesis.resume();
      setIsPaused(false);
      setIsSpeaking(true);
    } catch {
      // Ignore resume errors
    }
  }, [isSupported, isPaused]);

  const replay = useCallback(
    (text) => {
      const target = (text ?? lastSpokenTextRef.current ?? "").trim();
      if (!target) return false;
      return speak(target);
    },
    [speak]
  );

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const nextMuted = !prev;
      if (nextMuted && isSupported) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // Ignore
        }
        setIsSpeaking(false);
        setIsPaused(false);
      }
      return nextMuted;
    });
  }, [isSupported]);

  const setVolume = useCallback((nextVolume) => {
    const clamped = Math.min(1, Math.max(0, Number(nextVolume) || 0));
    setVolumeState(clamped);
  }, []);

  useEffect(() => {
    return () => {
      if (isSupported) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // Ignore
        }
      }
    };
  }, [isSupported]);

  return {
    isSupported,
    isSpeaking,
    isPaused,
    isMuted,
    volume,
    voices,
    selectedVoiceURI,
    setSelectedVoiceURI,
    setVolume,
    speak,
    pause,
    resume,
    replay,
    stop,
    toggleMute,
  };
}

