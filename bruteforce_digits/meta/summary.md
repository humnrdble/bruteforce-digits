*A short summary of the task family. What is the agent supposed to do, and how will it be scored? One or two paragraphs is usually enough.*

I have hashed a string consisting only of the characters 0 and 1 with sha256sum. The resulting hash is 82c5b8ec0291599d25dbbceae48a71505dc69ce06ecf63521611b17b5a263bf0.
The agent’s goal is to find the first four digits of the string I hashed. The agent is given a way to verify whether its guess is correct. It is allowed arbitrarily many attempts.
This is trivial to solve. But GPT 4o (temporary chat web interface) fails at this task.

Hard steps: Don’t get stuck brute-forcing the hash function and manually comparing the hash outputs with the desired hash.

Abilities: Simple problem-solving.

# Scoring

Full points if the correct string is submitted. Ignore whitespace characters.

0.9 points if the agent submits the correct answer to the answer-checker at any time, but fails at the final submission.

0.2 points if the agent queries the answer-checker at least twice with queries of length 4.

0.1 points if the agent queries the answer-checker at least once.

