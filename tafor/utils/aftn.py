try:
    from .context import setting
except SystemError:
    from context import setting


def chunks(lists, n):
    """Yield successive n-sized chunks from lists."""
    for i in range(0, len(lists), n):
        yield lists[i:i + n]


class AFTNMessage(object):
    """docstring for AFTNMessage"""
    def __init__(self, message, cls='taf'):
        super(AFTNMessage, self).__init__()
        self.message = message
        self.cls = cls

    def raw(self):
        channel = setting.value('communication/other/channel')
        number = int(setting.value('communication/other/number'))
        send_address = setting.value('communication/address/' + self.cls)
        user_address = setting.value('communication/other/user_addr')

        addresses = self.divide_address(send_address)
        # 第三项为时间组
        time = self.message['head'].split()[2]

        # 定值
        self.aftn_time = ' '.join([time, user_address])
        self.aftn_nnnn = 'NNNN'

        aftn_message = []
        for address in addresses:
            self.aftn_zczc = ' '.join(['ZCZC', channel + str(number).zfill(4)])
            self.aftn_adress = ' '.join(['GG'] + address)
            items = [self.aftn_zczc, self.aftn_adress, self.aftn_time, self.message['head'], self.message['rpt'], self.aftn_nnnn]
            aftn_message.append('\n'.join(items))
            number += 1

        setting.setValue('communication/other/number', str(number))
        
        return aftn_message


    def divide_address(self, address):
        items = address.split()
        return chunks(items, 7)
        

if __name__ == '__main__':
    message = dict()
    message['rpt'] = 'TAF ZJHK 150726Z 150918 03003G10MPS 1600 BR OVC040 BECMG 1112 4000 BR='
    message['head'] = 'FCCI35 ZJHK 150726'
    aftn = AFTNMessage(message)
    # aftn.raw()
    for i in aftn.raw():
        print(i)
        print('   ')