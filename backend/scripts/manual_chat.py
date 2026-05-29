from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ACTIVE_SESSION_ID: str | None = None


# 사용자가 터미널 테스트 종료를 요청했을 때 쓰는 예외
class QuitRequested(Exception):
    pass


# 입력값이 종료 명령인지 확인
def _is_quit_command(value: str) -> bool:
    return value.lower() in {"q", "/q", "quit", "exit"}


# 일반 입력을 받고 종료 명령이면, 예외 발생
def _input(prompt: str) -> str:
    value = input(prompt).strip()
    if _is_quit_command(value):
        raise QuitRequested
    return value


# 메뉴 선택 입력을 종료 예외 없이 그대로 받음
def _input_choice(prompt: str) -> str:
    return input(prompt).strip()


# 선택 입력값을 str 또는 None으로 받음
def _optional_text(prompt: str) -> str | None:
    value = _input(prompt)
    return value or None


# 종료 시 삭제할 현재 backend 세션 ID 저장
def _set_active_session_id(session_id: str | None) -> None:
    global ACTIVE_SESSION_ID
    ACTIVE_SESSION_ID = session_id


# 선택 입력값을 양의 정수 또는 None으로 받음
def _optional_int(prompt: str) -> int | None:
    while True:
        value = _input(prompt)
        if not value:
            return None
        number = _parse_int_text(value)
        if number is None:
            print("숫자로 입력해 주세요. 비우면 건너뜁니다.")
            continue
        if number < 0:
            print("0 이상의 숫자로 입력해 주세요.")
            continue
        return number


# 쉼표와 원 단위가 섞인 숫자 문자열 -> int로 변환
def _parse_int_text(value: str) -> int | None:
    cleaned = (
        value.strip()
        .replace(",", "")
        .replace("원", "")
        .replace(" ", "")
    )
    if not cleaned:
        return None
    if not cleaned.isdigit():
        return None
    return int(cleaned)


# 월소득 입력 -> 원 단위 정수로 변환
def _optional_krw(prompt: str) -> int | None:
    while True:
        value = _input(prompt)
        if not value:
            return None

        number = _parse_int_text(value)
        if number is None:
            print("금액은 예: 100,000원 또는 100000 처럼 입력해 주세요.")
            continue
        if number < 0:
            print("0원 이상의 금액으로 입력해 주세요.")
            continue

        print(f"입력한 월소득: {number:,}원 ({_format_korean_krw(number)})")
        return number


# 원 단위 금액 -> 한글 금액 표현
def _format_korean_krw(number: int) -> str:
    if number == 0:
        return "영원"

    group_units = ["", "만", "억", "조"]
    parts: list[str] = []
    group_index = 0
    remaining = number

    while remaining > 0 and group_index < len(group_units):
        group_number = remaining % 10000
        if group_number:
            korean = _format_under_10000(group_number)
            if group_number == 1 and group_units[group_index]:
                korean = ""
            parts.append(f"{korean}{group_units[group_index]}")
        remaining //= 10000
        group_index += 1

    return "".join(reversed(parts)) + "원"


# 10000 미만 숫자 -> 한글 숫자 표현
def _format_under_10000(number: int) -> str:
    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    units = ["천", "백", "십", ""]
    divisors = [1000, 100, 10, 1]
    parts: list[str] = []

    for divisor, unit in zip(divisors, units):
        digit = number // divisor
        number %= divisor
        if digit == 0:
            continue
        if digit == 1 and unit:
            parts.append(unit)
        else:
            parts.append(f"{digits[digit]}{unit}")

    return "".join(parts)


# 터미널에서 사용자 기본정보 입력
def ask_profile() -> dict[str, Any] | None:
    print("\n사용자 정보를 입력합니다. 모르면 Enter로 건너뛰세요.")

    age = _optional_int("나이: ")
    city = _optional_text("시/도 예: 경기도: ")
    district = _optional_text("시/군/구 예: 수원시: ")
    town = _optional_text("읍/면/동: ")
    monthly_income = _optional_krw("월소득 예: 100,000원: ")
    household_size = _optional_int("가구원 수: ")
    income_note = _optional_text("소득 관련 메모: ")

    location = {
        "city": city,
        "district": district,
        "town": town,
    }
    location = {key: value for key, value in location.items() if value is not None}

    profile: dict[str, Any] = {
        "age": age,
        "monthly_income_krw": monthly_income,
        "household_size": household_size,
        "income_note": income_note,
    }
    if location:
        profile["location"] = location

    profile = {key: value for key, value in profile.items() if value is not None}
    return profile or None


# backend /api/chat에 요청을 보내고 JSON 응답을 받음
def post_chat(base_url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
    url = f"{base_url.rstrip('/')}/api/chat"
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    print("\n답변 생성 중...", flush=True)

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print_http_error(exc.code, body)
        return None
    except TimeoutError:
        print(f"요청 시간이 {timeout}초를 넘었습니다. RAG나 LLM 응답이 늦는지 서버 로그를 확인하세요.")
        return None
    except URLError as exc:
        print("\n백엔드 서버에 연결할 수 없습니다.")
        print(f"- 원인: {exc.reason}")
        print("- backend 서버가 켜져 있는지, 포트가 맞는지 확인하세요.")
        return None

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print("\n백엔드가 JSON이 아닌 응답을 반환했습니다.")
        print(body)
        return None


# backend 세션 메모리 삭제
def delete_chat_session(base_url: str, session_id: str | None, timeout: int) -> None:
    if not session_id:
        return

    url = f"{base_url.rstrip('/')}/api/chat/session/{session_id}"
    request = Request(
        url,
        headers={"Accept": "application/json"},
        method="DELETE",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response.read()
    except (HTTPError, TimeoutError, URLError):
        print("\n세션 메모리 삭제 요청에 실패했습니다.")


# backend HTTP 오류 응답을 사용자에게 읽기 쉬운 형태로 출력
def print_http_error(status_code: int, body: str) -> None:
    print(f"\n백엔드 오류가 발생했습니다. HTTP {status_code}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return

    detail = data.get("detail", data)
    if isinstance(detail, list):
        print("요청 형식이 맞지 않습니다.")
        for item in detail:
            loc = " -> ".join(str(part) for part in item.get("loc", []))
            msg = item.get("msg", "validation error")
            print(f"- {loc}: {msg}")
        return

    print(detail)


# 답변 텍스트를 지정한 속도로 터미널에 출력
def _stream_text(text: str, delay: float) -> None:
    if delay <= 0:
        print(text)
        return

    for character in text:
        print(character, end="", flush=True)
        time.sleep(delay)
    print()


# backend 응답 JSON을 사용자에게 보이는 상담 답변 형태로 출력
def render_response(response: dict[str, Any], stream_delay: float) -> None:
    print("\n" + "=" * 72)

    summary = response.get("summary")
    if summary:
        print("\n[답변]")
        _stream_text(summary, stream_delay)

    details = response.get("details") or []
    if details:
        print("\n[상세]")
        for detail in details:
            _stream_text(f"- {detail}", stream_delay)

    laws = response.get("laws") or []
    if laws:
        print("\n[관련 법령]")
        for law in laws:
            name = law.get("name", "-")
            article = law.get("article", "-")
            url = law.get("url")
            print(f"- {name} {article}" + (f" ({url})" if url else ""))

    table = response.get("table")
    if table:
        print("\n[표]")
        headers = table.get("headers") or []
        rows = table.get("rows") or []
        if headers:
            print(" | ".join(str(header) for header in headers))
            print("-+-".join("-" * len(str(header)) for header in headers))
        for row in rows:
            print(" | ".join(str(cell) for cell in row))

    references = response.get("references") or []
    if references:
        print("\n[출처]")
        for index, ref in enumerate(references, start=1):
            title = ref.get("title") or "-"
            file_name = ref.get("file_name") or "-"
            section = ref.get("section") or "-"
            url = ref.get("url") or "-"
            print(f"{index}. {title} / {file_name} / {section}")
            print(f"   URL: {url}")
            excerpt = ref.get("excerpt")
            if excerpt:
                print(f"   근거: {excerpt}")

    sources = response.get("sources") or []
    if sources and not references:
        print("\n[출처]")
        for source in sources:
            print(f"- {source}")

    warning = response.get("warning")
    if warning:
        print("\n[주의]")
        print(warning)

    print("=" * 72)


# 보기 응답에서 사용자가 선택/기타 입력
def choose_clarification(response: dict[str, Any]) -> tuple[str, dict[str, Any] | str | None]:
    options = response.get("options") or []
    if not options:
        return "none", None

    print("\n보기 중 하나를 고르거나 기타를 입력할 수 있습니다.")
    for option in options:
        print(f"{option['id']}. {option['title']}")
        print(f"   {option.get('description', '')}")
    if response.get("allow_custom_input"):
        print("4. 기타 직접 입력")

    while True:
        choice = _input_choice("선택 [1/2/3/4, 다시질문 r, 종료 q]: ").lower()
        if _is_quit_command(choice):
            return "quit", None
        if choice == "r":
            return "retry", None
        if choice in {"1", "2", "3"}:
            for option in options:
                if option.get("id") == choice:
                    return "selected", option
            print("응답에 해당 보기가 없습니다.")
            continue
        if choice == "4" and response.get("allow_custom_input"):
            while True:
                custom_intent = _input("기타 내용을 입력하세요: ")
                if custom_intent:
                    return "custom", custom_intent
                print("기타 내용은 비워둘 수 없습니다.")
        print("1, 2, 3, 4, r, q 중 하나를 입력하세요.")


# 답변 후, 다음 행동을 사용자가 선택
def ask_next_mode(can_go_back: bool) -> str:
    print("\n다음에 무엇을 할까요?")
    print("1. 후속 질문")
    print("2. 새 질문")
    print("3. 사용자 정보 다시 입력")
    if can_go_back:
        print("4. 이전 보기로 돌아가기")
        print("5. 종료")
        prompt = "선택 [1/2/3/4/5, 종료 q]: "
    else:
        print("4. 종료")
        prompt = "선택 [1/2/3/4, 종료 q]: "

    while True:
        choice = _input_choice(prompt)
        if _is_quit_command(choice):
            return "quit"
        if choice == "1":
            return "follow_up"
        if choice == "2":
            return "new_question"
        if choice == "3":
            return "profile"
        if choice == "4" and can_go_back:
            return "back_to_options"
        if choice == "4" and not can_go_back:
            return "quit"
        if choice == "5" and can_go_back:
            return "quit"
        print("번호를 다시 확인해 주세요.")


# 수동 대화 테스트의 전체 입력/요청/출력 루프 실행
def run(base_url: str, timeout: int, stream_delay: float) -> int:
    print("백엔드 수동 대화 테스트")
    print(f"API: {base_url.rstrip('/')}/api/chat")
    print("종료하려면 입력 위치에서 q 를 입력하세요. /q, quit, exit도 가능합니다.")

    session_id: str | None = None
    profile = ask_profile()
    profile_dirty = profile is not None
    mode = "new_question"
    last_clarification_response: dict[str, Any] | None = None
    last_clarification_question: str | None = None

    while True:
        if mode == "profile":
            profile = ask_profile()
            profile_dirty = profile is not None
            mode = "new_question"
            continue

        if mode == "back_to_options":
            if last_clarification_response is None or last_clarification_question is None:
                print("\n돌아갈 보기가 없습니다.")
                mode = "new_question"
                continue
            handled = handle_clarification_choice(
                base_url=base_url,
                timeout=timeout,
                stream_delay=stream_delay,
                response=last_clarification_response,
                question=last_clarification_question,
                session_id=session_id,
            )
            if handled == "quit":
                return 0
            if isinstance(handled, str):
                session_id = handled
            next_mode = ask_next_mode(can_go_back=True)
            if next_mode == "quit":
                return 0
            mode = next_mode
            continue

        label = "후속 질문" if mode == "follow_up" else "질문"
        question = _input(f"\n{label}: ")
        if not question:
            print("질문은 비워둘 수 없습니다.")
            continue

        payload: dict[str, Any] = {"question": question}
        if session_id:
            payload["session_id"] = session_id
        if mode == "follow_up":
            payload["is_follow_up"] = True
        if profile_dirty and profile is not None:
            payload["user_profile"] = profile

        response = post_chat(base_url, payload, timeout)
        if response is None:
            next_mode = ask_next_mode(can_go_back=last_clarification_response is not None)
            if next_mode == "quit":
                return 1
            mode = next_mode
            continue

        session_id = response.get("session_id") or session_id
        _set_active_session_id(session_id)
        profile_dirty = False
        render_response(response, stream_delay)

        if response.get("kind") == "clarification":
            last_clarification_response = response
            last_clarification_question = question
            handled = handle_clarification_choice(
                base_url=base_url,
                timeout=timeout,
                stream_delay=stream_delay,
                response=response,
                question=question,
                session_id=session_id,
            )
            if handled == "quit":
                return 0
            if handled == "retry":
                mode = "new_question"
                continue
            if isinstance(handled, str):
                session_id = handled
                _set_active_session_id(session_id)

        next_mode = ask_next_mode(can_go_back=last_clarification_response is not None)
        if next_mode == "quit":
            return 0
        mode = next_mode


# 보기 선택/기타 입력 후, backend에 후속 요청
def handle_clarification_choice(
    base_url: str,
    timeout: int,
    stream_delay: float,
    response: dict[str, Any],
    question: str,
    session_id: str | None,
) -> str | None:
    action, value = choose_clarification(response)
    if action in {"quit", "retry"}:
        return action
    if action not in {"selected", "custom"}:
        return None

    follow_payload: dict[str, Any] = {
        "session_id": session_id,
        "question": question,
    }
    if action == "selected":
        follow_payload["selected_option"] = value
    else:
        follow_payload["custom_intent"] = value

    follow_response = post_chat(base_url, follow_payload, timeout)
    if follow_response is None:
        return session_id

    next_session_id = follow_response.get("session_id") or session_id
    _set_active_session_id(next_session_id)
    render_response(follow_response, stream_delay)
    return next_session_id


# 터미널 실행 옵션 파싱
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend /api/chat manual terminal tester")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL. Default: http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout seconds. Default: 90",
    )
    parser.add_argument(
        "--stream-delay",
        type=float,
        default=0.004,
        help="Seconds between printed answer characters. Use 0 to disable. Default: 0.004",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = 0
    try:
        exit_code = run(**vars(args))
    except QuitRequested:
        print("\n종료합니다.")
    except KeyboardInterrupt:
        print("\n종료합니다.")
        exit_code = 130
    finally:
        delete_chat_session(args.base_url, ACTIVE_SESSION_ID, args.timeout)

    sys.exit(exit_code)
