# You'll need to install PyJWT via pip 'pip install PyJWT' or your project packages file

import jwt
import time


METABASE_SECRET_KEY = "e1360f8d14ee2ca201c2b7624128c0dd622cc0aa60bd7983a400f8346e7fd5bf"

payload = {
  "resource": {"dashboard": 3},
  "params": {
    
  },
  "exp": round(time.time()) + (6000000 * 10) # 10 minute expiration
}
token = jwt.encode(payload, METABASE_SECRET_KEY, algorithm="HS256")

print(token)