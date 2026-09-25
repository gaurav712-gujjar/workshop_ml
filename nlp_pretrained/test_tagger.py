from nlp_pretrained.ner_tagger import extract_entities

# Test 1
text1 = "Gaurav is working at Regex Software in Jaipur."

entities1 = extract_entities(text1)

print("\nTest 1")
print("Text:", text1)
print("Entities:", entities1)


# Test 2
text2 = "Narendra Modi visited New Delhi and met Microsoft executives."

entities2 = extract_entities(text2)

print("\nTest 2")
print("Text:", text2)
print("Entities:", entities2)


# Test 3
text3 = "Elon Musk is the CEO of Tesla and lives in California."

entities3 = extract_entities(text3)

print("\nTest 3")
print("Text:", text3)
print("Entities:", entities3)