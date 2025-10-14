gen_ex = (x for x in range(3))
list_from_gen = set(map(list(gen_ex))) # Converted to set after nested calls
for _i in range(2):
    for item in list_from_gen:
        print(item)