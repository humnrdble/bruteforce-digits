import sys

def notnumbers(s):
    for char in s:
        if char not in ["0", "1"]:
            return True
    return False

secret = "1101"

print("Check your answer:")
userinput = input()
userinput = userinput.replace("\"", "\'").replace("\n","").replace("\r","")

with open('agent.log', 'a') as log:
    #when reading log: for counting lines, remove newline!
    log.write('"'+ userinput + '"' + "\n")

    if len(userinput) != 4 or notnumbers(userinput):
        print("malformed query")
        sys.exit(1)


    #constant-time comparison
    match = True
    for i in range(4):
        match = (secret[i] == userinput[i]) and match
        
    if match:
        print("correct")
    else:
        print("wrong answer")