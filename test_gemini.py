from google import genai

client = genai.Client(
    vertexai=True,
    project="procurement-fde-agent",
    location="us-central1"
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="สวัสดี ช่วยแนะนำตัวสั้นๆ หน่อย"
)

print(response.text)