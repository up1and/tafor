
lists = ['aaa', 'dsds', '', '', 'bbbb']

lists2 = filter(None, lists)


rpt = '\n'.join(lists2)

print(rpt)