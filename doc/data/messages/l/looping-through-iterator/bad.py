gen_ex = (x for x in range(3)) # Module level: module_node.body[0]
for _i in range(2):            # Outer loop: module_node.body[1]
    for item in gen_ex:        # Inner loop: module_node.body[1].body[0]
        print(item)