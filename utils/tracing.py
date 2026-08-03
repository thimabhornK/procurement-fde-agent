"""
Tracing และ metrics พื้นฐานสำหรับวัดประสิทธิภาพของการเรียก LLM
เก็บ latency, จำนวน token, และประมาณการค่าใช้จ่ายต่อการเรียกแต่ละครั้ง
นี่คือจุดเริ่มต้นของ observability framework ที่ต้องมีในระบบ agentic แบบ production
"""

import time


class Tracer:
    def __init__(self):
        self.records = []

    def log(self, node_name: str, latency_sec: float, response, config):
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None

        estimated_cost = None
        if input_tokens is not None and output_tokens is not None:
            estimated_cost = (
                input_tokens / 1000 * config.COST_PER_1K_INPUT_TOKENS
                + output_tokens / 1000 * config.COST_PER_1K_OUTPUT_TOKENS
            )

        self.records.append(
            {
                "node": node_name,
                "latency_sec": round(latency_sec, 3),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": round(estimated_cost, 6) if estimated_cost is not None else None,
            }
        )

    def summary(self) -> str:
        lines = ["=== Trace summary ==="]
        total_cost = 0.0
        total_latency = 0.0
        for r in self.records:
            lines.append(
                f"[{r['node']}] latency={r['latency_sec']}s "
                f"tokens_in={r['input_tokens']} tokens_out={r['output_tokens']} "
                f"cost=${r['estimated_cost_usd']}"
            )
            total_latency += r["latency_sec"]
            if r["estimated_cost_usd"]:
                total_cost += r["estimated_cost_usd"]
        lines.append(f"รวม latency: {round(total_latency, 3)} วินาที")
        lines.append(f"รวมค่าใช้จ่ายโดยประมาณ: ${round(total_cost, 6)}")
        return "\n".join(lines)


def generate(client, config, contents, node_name: str, tracer: Tracer = None):
    """เรียก Gemini พร้อมวัด latency/token/cost ถ้ามี tracer ส่งเข้ามาด้วย"""
    start = time.time()
    response = client.models.generate_content(model=config.GEMINI_MODEL, contents=contents)
    elapsed = time.time() - start

    if tracer is not None:
        tracer.log(node_name, elapsed, response, config)

    return response
