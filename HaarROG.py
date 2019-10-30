'''
путь до изображения:
path + keys[]

объект:
x1:testData[keys[0]]['regions']['0']['shape_attributes']['x']
y1:testData[keys[0]]['regions']['0']['shape_attributes']['y']
x2:testData[keys[0]]['regions']['0']['shape_attributes']['x'] + testData[keys[0]]['regions']['0']['shape_attributes']['width']
y2:testData[keys[0]]['regions']['0']['shape_attributes']['y'] + testData[keys[0]]['regions']['0']['shape_attributes']['height']

количество объектов:
len(y1:testData[keys[0]]['regions'])
'''

#Для форматированя данных в программе использован json
'''
"1_11_2014_12_13_38_590.bmp38467": {
  "fileref": "",
  "size": 38467,
  "filename": "1_11_2014_12_13_38_590.bmp",
  "base64_img_data": "",
  "file_attributes": {},
  "regions": {
    "0": {
      "shape_attributes": {
        "name": "rect",
        "x": 186,
        "y": 203,
        "width": 75,
        "height": 21
      },
      "region_attributes": {}
    }
  }
}
'''
#-----------------------------------------------------------------------

import math
import random

import cv2
import numpy as np
from google.colab.patches import cv2_imshow

#для хранения данных используем json, наиболее удобный формат
import json

#метрики
from sklearn.metrics import roc_auc_score
from sklearn.metrics import roc_curve
from sklearn.metrics import average_precision_score

#Построение графиков
import matplotlib.pyplot as plt

#-----------------------------------------------------------------------
#вспомогательные процедуры

def changeOpCharac(dataList, markedData, key, rateCh):
    #список для найденных уникальных номерных пластин
    #список для общего количества найденных номерных пластин
    findPlates = []
    findUnicPlates = []
    localList = dataList.copy()

    for i in range(len(localList)):
        x1 = 0
        x2 = 0
        y1 = 0
        y2 = 0

        mx1 = 0
        mx2 = 0
        my1 = 0
        my2 = 0

        #в данном случае очень важная нумерация с нуля
        for j in range(len(markedData[key]['regions'])):
            #формируем список для размеченных данных из json
            markedNumPlatesList = [
                         markedData[key]['regions'][str(j)]['shape_attributes']['x'],
                         markedData[key]['regions'][str(j)]['shape_attributes']['y'],
                         markedData[key]['regions'][str(j)]['shape_attributes']['x'] + markedData[key]['regions'][str(j)]['shape_attributes']['width'],
                         markedData[key]['regions'][str(j)]['shape_attributes']['y'] + markedData[key]['regions'][str(j)]['shape_attributes']['height']
                        ]

            #print('LL')
            #print(localList)
            #print('MNPL')
            #print(markedNumPlatesList)

            #x1 < x2
            #упорядочили по x
            if localList[i][0] < localList[i][2]:
                x1 = localList[i][0]
                x2 = localList[i][2]
            else:
                x1 = localList[i][2]
                x2 = localList[i][0]

            #упорядочили по x
            if markedNumPlatesList[0] < markedNumPlatesList[2]:
                mx1 = markedNumPlatesList[0]
                mx2 = markedNumPlatesList[2]
            else:
                mx1 = markedNumPlatesList[2]
                mx2 = markedNumPlatesList[0]

            #y1 < y2
            #упорядочили по y
            if localList[i][1] < localList[i][3]:
                y1 = localList[i][1]
                y2 = localList[i][3]
            else:
                y1 = localList[i][3]
                y2 = localList[i][1]

            #упорядочили по x
            if markedNumPlatesList[1] < markedNumPlatesList[3]:
                my1 = markedNumPlatesList[1]
                my2 = markedNumPlatesList[3]
            else:
                my1 = markedNumPlatesList[3]
                my2 = markedNumPlatesList[1]

            #print(x1, x2, mx1, mx2, y1, y2, my1, my2)

            #находим пересечение отрезков
            xIntersection = max(0, min(x2, mx2) - max(x1, mx1))
            yIntersection = max(0, min(y2, my2) - max(y1, my1))
            #print('xIntersection ' + str(xIntersection))
            #print('yIntersection ' + str(yIntersection))


            #вычисляем площади
            detectNumArea = math.sqrt((x2 - x1)**2) * math.sqrt((y2 - y1)**2)
            detectNumAreaInter = xIntersection * yIntersection
            numArea = math.sqrt((markedNumPlatesList[0] - markedNumPlatesList[2])**2) * math.sqrt((markedNumPlatesList[1] - markedNumPlatesList[3])**2)

            #print('detectNumArea: ' + str(detectNumArea))
            #print('detectNumAreaInter: ' + str(detectNumAreaInter))
            #print('numArea: ' + str(numArea))
            #print('detectNumAreaInter / numArea: ' + str(detectNumAreaInter / numArea))
            #print('detectNumArea / numArea: ' + str(detectNumArea / numArea))

            if (detectNumAreaInter / numArea > lowerBorder) and (detectNumArea / numArea < topBorder):
                findPlates.append(str(j))

            if (detectNumAreaInter / numArea > lowerBorder) and (detectNumArea / numArea < topBorder) and (str(j) not in findUnicPlates):
                findUnicPlates.append(str(j))

    #print(findPlates, ' findPlates')
    #print(localList, ' localList')
    #print(findUnicPlates, ' findUnicPlates')
    #print(len(markedData[key]['regions']), ' len(markedData[key][\'regions\'])')

    rateCh.tp += len(findPlates)
    rateCh.fp += len(localList) - len(findPlates)
    rateCh.fn += len(markedData[key]['regions']) - len(findUnicPlates)
    if len(markedData[key]['regions']) == 0 and len(findPlates) == 0:
        rateCh.tn += 1

    return rateCh

def drawMarkAndDetect(detectReg, markedRegions, itemKey):
    markedNumPlates = []
    for i in range(len(markedRegions[itemKey]['regions'])):
        batch = []
        batch.append(markedRegions[itemKey]['regions'][str(i)]['shape_attributes']['x'])
        batch.append(markedRegions[itemKey]['regions'][str(i)]['shape_attributes']['y'])
        batch.append(markedRegions[itemKey]['regions'][str(i)]['shape_attributes']['width'])
        batch.append(markedRegions[itemKey]['regions'][str(i)]['shape_attributes']['height'])
        markedNumPlates.append(batch)

    for (x, y, w, h) in detectReg:
        cv2.rectangle(image, (x, y), (x + w, y + h), (random.randint(50, 250), 232, random.randint(50, 250)), -1)

    for (x, y, w, h) in markedNumPlates:
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 250, 250), 2)

    cv2_imshow(image)
    cv2.waitKey(0)


#-----------------------------------------------------------------------
#Paths

#cascade.xml
#haarcascade_russian_plate_number.xml

haarPath = "/content/haarcascade_russian_plate_number.xml"
dataPath = '/content/numplates_region_data.json'
drivePath = '/content/drive/My Drive/testData/'

print('CV2 version: ')
print(cv2.__version__ + '\n')

#-----------------------------------------------------------------------
#загрузка данных

#загружаем каскад
numplateCascade = cv2.CascadeClassifier(haarPath)

#загружаем файл с размеченной тестовой выборкой
with open(dataPath, "r") as read_file:
    testData = json.load(read_file)
    #создаем список ключей в словаре
    keys = list(testData.keys())


#-----------------------------------------------------------------------
#тестирование

class Characteristics:
    #положительные характеристики
    tp = 0
    tn = 0
    #отрицательные характеристики
    fp = 0
    fn = 0

rateCh = Characteristics()

#border для определения, правильно найден номер или не правильно
#для площади пересечения номерных рамок
lowerBorder = 0.7
topBorder = 1.8

#два списка для составления ROC-кривой
fprList = []
tprList = []

#точки, для построения графика
points = [1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5]
numNeigh = [1, 3, 5, 7]

#временная переменная для фикрисорованного количества итераций (вместо len(keys)) iterKeys = 4

for pIter in range(len(points)):
    rateCh.tp = 0
    rateCh.tn = 0
    rateCh.fp = 0
    rateCh.fn = 0
    #проходимся по всем тестовым картинкам

    for numIter in range(len(numNeigh)):

        for i in range(len(keys) // 5):

            #для удобства сохраним ключ в отдельную переменную
            itemKey = keys[i]

            print('----------------------------------------------------')
            print(str(i) + '. ' + testData[itemKey]['filename'])

            #преобразуем изображение
            image = cv2.imread(drivePath + testData[itemKey]['filename'])
            if image is None:
                continue

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            #определяем, присутствует ли номерная пластина
            #характеристики нужно менять, при оценке каскада
            numPlates = numplateCascade.detectMultiScale(
                gray,
                scaleFactor = points[pIter],
                minNeighbors = numNeigh[numIter]
            )

            detectData = []
            #для того, чтобы не появлялась ошибка, когда каскад не нашел номерных пластин
            #создаем список в удобном для нас формате, т.к. для numPlates характерна запись (x, y, w, h)
            if len(numPlates) == 0:
                detectData = []
            else:
              for i in range(len(numPlates)):
                bufData = [numPlates[i][0], numPlates[i][1], numPlates[i][0] + numPlates[i][2], numPlates[i][1] + numPlates[i][3]]
                detectData.append(bufData)

            #numPlates это список из списков [[],[]]
            #передаем в функцию list с найденными номерами и размеченные данные
            #данная функция увеличит tpr
            rateCh = changeOpCharac(detectData, testData, itemKey, rateCh)

            print('   TP: ' + str(rateCh.tp) + ' TN: ' + str(rateCh.tn) + ' FP: ' + str(rateCh.fp) + ' FN: ' + str(rateCh.fn))
            print('   Number of license plates: ', len(testData[itemKey]['regions']))
            print('   Found: {0} numplate!'.format(len(numPlates)))
            print('----------------------------------------------------')

            #обнуляем
            #rateCh.tp = 0
            #rateCh.tn = 0
            #rateCh.fp = 0
            #rateCh.fn = 0


            #drawMarkAndDetect(numPlates, testData, itemKey)

    #считаем fpr и trp (учитываем деление на ноль)
    try:
      tprList.append(rateCh.tp / (rateCh.tp + rateCh.fn))
      print('tpr:' + str(rateCh.tp / (rateCh.tp + rateCh.fn)))
    except:
      tprList.append(0)

    try:
      fprList.append(rateCh.fp / (rateCh.fp + rateCh.tn))
      print('fpr:' + str(rateCh.fp / (rateCh.fp + rateCh.tn)))
    except:
      fprList.append(0)
#Следующим шагом вычислим ROC-AUC и PR-AUC и построим ROC-кривую для оценки точности полученной модели:

print("ROC-AUC: ", 0)
print("PR-AUC: ", 0)

print(fprList)
print(tprList)

plt.plot(fprList, tprList, color='r', label='Log Res')
plt.title('ROC curve for Log Res')
plt.plot([0, 1], [0, 1], color='navy', linestyle='--')
plt.xlabel('FPR')
plt.ylabel('TPR')
plt.grid()
plt.show()
plt.gcf().clear()