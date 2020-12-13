from modules.plugin_manager.structure import Plugin, Chart, Image
from random import randint
import matplotlib.pyplot as plt


class Main(Plugin):
    name = 'тест'
    description = 'описание'
    chart1 = Chart(chart_type='line',
                   data={"labels": 'Red', "datasets": [
                       {"code": '1', "label": 'линия', "backgroundColor": 'green', "borderColor": 'green',
                        "fill": "false", "borderWidth": 1,
                        "pointRadius": '1', "data": []}]},
                   options={"scales": {"xAxes": [
                       {"type": 'linear', "position": 'bottom', "scaleLabel": {"display": True, "labelString": 'x'}}],
                                       "yAxes": [{"scaleLabel": {"display": True, "labelString": 'y'}}]},
                            "legend": {"display": True,
                                       "labels": {"usePointStyle": False, "boxWidth": 5, "fontSize": 12}}})
    chart1.set_layout(position={'x':20,'y':20},size={'h':20,'w':45})

    image = Image()
    image.set_layout(position={'x':70,'y':20},size={'h':20,'w':20})

    data = [{"x": 1, "y": 1}]

    def generate_plot(self):
        plt.figure()
        plt.plot([x['x'] for x in self.data], [y['y'] for y in self.data])
        plt.xlabel("x")
        plt.ylabel("y")
        plt.title("Линия")
        return plt

    def main(self):
        self.add_widget(self.chart1, self.image)  # Добавляем виджеты на экран

        @self.on_command('test') # подписываемся на команду
        async def a(*args):
            generated = {'x':self.data[-1]['x']+1,'y':randint(-22,22)}
            self.data.append(generated)
            self.chart1.data['datasets'][0]['data']=self.data
            await self.image.update(plot=self.generate_plot())
            await self.chart1.update()
            await self.send_message(str(generated))
            t = await self.con_input('m')
            await self.send_message(str(t))

        @self.on_command('cls')
        async def cls(*args):
            self.data.clear()
            self.chart1.data['datasets'][0]['data'].clear()
            await self.image.update(plot=self.generate_plot())
            await self.chart1.update()
            await self.send_message('Очищено')


Main().main()
