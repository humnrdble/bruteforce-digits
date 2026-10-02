import sys

def notnumbers(s):
    for char in s:
        if char not in ["0", "1"]:
            return True
    return False

secret = "1101"

if len(sys.argv) > 1:
    userinput = sys.argv[1]
else:
    print("Check your answer:")
    userinput = input()
userinput = userinput.replace("\"", "\'").replace("\n","").replace("\r","")

for log_path in ['/root/agent.log', 'agent.log']:
    try:
        with open(log_path, 'a') as log:
            log.write('"'+ userinput + '"' + "\n")
        break
    except Exception:
        continue

if len(userinput) != 4 or notnumbers(userinput):
    print("malformed query")
    sys.exit(1)


#constant-time comparison
match = True
for i in range(4):
    match = (secret[i] == userinput[i]) and match
    
if match:
    print("correct answer")
else:
    print("wrong answer")