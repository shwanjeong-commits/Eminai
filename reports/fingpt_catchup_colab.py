from google.colab import files


uploaded = files.upload()
report_filename = next(iter(uploaded))
report_text = uploaded[report_filename].decode("utf-8")

instruction = """
Analyze the following verified US and South Korean financial-market data.

Return:
1. US financial sentiment: positive, neutral, or negative
2. South Korean financial sentiment: positive, neutral, or negative
3. Three bullish facts
4. Three bearish facts
5. Main equity, bond, FX, oil, and semiconductor implications
6. The most important risk to monitor

Use only information contained in the input.
Do not create missing figures or events.
Separate reported facts from your interpretation.
"""

# Use tokenizer-aware chunks and leave room for the instruction and answer.
token_ids = tokenizer.encode(report_text, add_special_tokens=False)
chunk_size = 700
token_chunks = [token_ids[i : i + chunk_size] for i in range(0, len(token_ids), chunk_size)]
chunks = [tokenizer.decode(chunk, skip_special_tokens=True) for chunk in token_chunks]

chunk_reviews = []
for number, chunk in enumerate(chunks, start=1):
    result = ask_fingpt(
        instruction + f"\nThis is report section {number} of {len(chunks)}.",
        chunk,
        max_new_tokens=220,
    )
    chunk_reviews.append(result)
    print(f"\n--- Section {number} review ---\n{result}")

combined_reviews = "\n\n".join(
    f"Section {index}:\n{review}"
    for index, review in enumerate(chunk_reviews, start=1)
)

final_instruction = """
Synthesize the section reviews into one concise financial-market assessment in English.
Do not add facts that are absent from the reviews.
Return: regime, US outlook, Korean outlook, cross-market transmission,
base/bull/bear scenarios, and a next-two-week watchlist.
Avoid repetition. Use short bullet points.
"""

print("\n=== FinGPT final assessment ===")
print(ask_fingpt(final_instruction, combined_reviews, max_new_tokens=300))
