a = {
    "b":{"c":3}
}
b = a.get('b')

c = {'xx':b}
print (a)

c.get('xx')['c'] = 100

print(a)