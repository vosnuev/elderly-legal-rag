# Wrong-Question Dataset For With-Tool Runs

no-tool LLM judge에서 `wrong`으로 판정된 문제만 모아 with-tool 재실행을 준비하는 데이터셋이다.

목적:

- no-tool에서 틀린 문제만 tool 연결 후 다시 실행한다.
- with-tool accuracy improvement를 모델별로 비교한다.
- 오답 구간만 실행해 cost efficiency를 확인한다.
- 추후 wrong-only 개선율을 전체 문항 기준 expected overall accuracy로 환산한다.

## Files

| Path | Purpose |
| --- | --- |
| `wrong_questions_all_models.csv` | 모든 모델의 no-tool 오답 model-question pair 405개 |
| `wrong_questions_unique.csv` | 모델 중 하나라도 틀린 고유 질문 183개 |
| `wrong_questions_summary.csv` | 모델별 no-tool 오답 수와 wrong rate |
| `wrong_questions__*.csv` | 모델별 no-tool 오답만 모은 with-tool 실행 후보 |

모델별 오답 수:

| Model | Provider | Wrong Questions |
| --- | --- | ---: |
| `openai/gpt-oss-120b` | `cerebras` | 132 |
| `deepseek/deepseek-v4-flash` | `deepseek` | 111 |
| `deepseek/deepseek-v4-pro` | `deepseek` | 86 |
| `qwen/qwen3.7-plus` | `alibaba` | 76 |

각 row에는 no-tool answer/judge reason과 기준 정보가 들어 있고, with-tool 실행 결과를 채울 빈 컬럼도 포함한다.
