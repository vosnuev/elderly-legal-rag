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
    min-height: 42px;
    padding: 0 0.9rem;
    border: 1.5px solid #4A2E1A;
    border-radius: 8px;
    background: #FFFDF7;
    color: #4A2E1A;
    font-family: "Noto Sans KR", system-ui, sans-serif;
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.2;
    white-space: nowrap;
    cursor: pointer;
    box-shadow: none;
    transition:
        background 0.16s ease,
        border-color 0.16s ease,
        box-shadow 0.16s ease,
        color 0.16s ease;
}

#use-location:hover:not(:disabled) {
    background: #E8E6DC;
    border-color: #3a2010;
    color: #3a2010;
    box-shadow: none;
}

#use-location:focus-visible {
    outline: 2px solid #4A2E1A;
    outline-offset: 2px;
}

#use-location:disabled {
    border-color: #8F7A6A;
    background: #E8E6DC;
    color: #8F7A6A;
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
