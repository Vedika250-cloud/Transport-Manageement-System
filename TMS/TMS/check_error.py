import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:5000/dashboard')
except Exception as e:
    print(e.read().decode())
