from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st


_GEOLOCATION_BUTTON = st.components.v2.component(
    "geolocation_text_button",
    html='<button id="use-location" type="button">내 위치 사용하기</button>',
    css="""
#use-location {
    width: 100%;
    min-height: 44px;
    padding: 0 0.9rem;
    border: 1px solid #DDE3EE;
    border-radius: 8px;
    background: #FFFFFF;
    color: #1F2937;
    font-family: inherit;
    font-size: 0.92rem;
    font-weight: 800;
    line-height: 1.2;
    white-space: nowrap;
    cursor: pointer;
}

#use-location:hover:not(:disabled) {
    background: #F8FAFC;
    border-color: #CBD5E1;
}

#use-location:focus-visible {
    outline: 3px solid rgba(139, 92, 246, 0.22);
    outline-offset: 2px;
}

#use-location:disabled {
    color: #94A3B8;
    cursor: wait;
}
""",
    js="""
export default function (component) {
  const { parentElement, setTriggerValue } = component
  const button = parentElement.querySelector("#use-location")
  if (!button || button.dataset.bound === "true") return

  const reset = () => {
    button.disabled = false
    button.textContent = "내 위치 사용하기"
  }

  button.dataset.bound = "true"
  button.onclick = () => {
    if (!navigator.geolocation) {
      setTriggerValue("error", {
        message: "이 브라우저에서는 위치 기능을 사용할 수 없습니다.",
        timestamp: Date.now(),
      })
      return
    }

    button.disabled = true
    button.textContent = "위치 확인 중"

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setTriggerValue("location", {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          altitude: position.coords.altitude,
          accuracy: position.coords.accuracy,
          altitudeAccuracy: position.coords.altitudeAccuracy,
          heading: position.coords.heading,
          speed: position.coords.speed,
          timestamp: Date.now(),
        })
        reset()
      },
      (error) => {
        setTriggerValue("error", {
          code: error.code,
          message: error.message,
          timestamp: Date.now(),
        })
        reset()
      },
      {
        enableHighAccuracy: false,
        timeout: 10000,
        maximumAge: 300000,
      },
    )
  }
}
""",
)


def render_geolocation_button(*, key: str) -> dict[str, Any] | None:
    result = _GEOLOCATION_BUTTON(
        key=key,
        on_location_change=lambda: None,
        on_error_change=lambda: None,
    )
    error = getattr(result, "error", None)
    if isinstance(error, Mapping):
        st.session_state["location_error"] = dict(error)
    else:
        st.session_state.pop("location_error", None)
    location = getattr(result, "location", None)
    if not isinstance(location, Mapping):
        return None
    st.session_state.pop("location_error", None)
    return dict(location)
