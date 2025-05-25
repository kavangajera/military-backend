from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

prompt = """ write only python code **NO EXPLANATION** to scrape the following wikipedia page https://en.wikipedia.org/wiki/List_of_military_operations_of_India and return well structured json file 
 ** make sure code is errorless and you know the content of the given page very well it may be in tabular form**
"""

print(os.getenv("MILITARY_API_KEY"))
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("MILITARY_API_KEY"),   
)

completion = client.chat.completions.create(
  model="mistralai/devstral-small:free",
  messages=[
    {
      "role": "user",
      "content": prompt,
    }
  ]
)
print(completion.choices[0].message.content)