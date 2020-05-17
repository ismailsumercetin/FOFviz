from django.shortcuts import render
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from plotly.offline import plot
import plotly.graph_objects as go
import plotly.express as px
import pmdarima as pm
from pmdarima import model_selection
import datetime
import pandas as pd
import os.path
import DataRetrieve
from sqlalchemy import create_engine
import operator
import wikipedia

counterSector = 1
counterSectorArray = [counterSector]
showPredictions = False
plotDictionary = {'Line Plot': 'line', 'Stacked Bar Chart' : 'bar', 'Grouped Bar Chart' : 'bar', 
'Scatter Plot': 'scatter', 'Alluvial Diagram': 'parallel_categories', 'Area Graph': 'area', 
'Density Contour': 'density_contour','Heat Map': 'density_heatmap'}
ops_dictionary = { "+": operator.add, "-": operator.sub, "*": operator.mul }


#determine selection
selectedPreviousDataName = None
selectedDataName = None
selectedSectors = [None,None,None,None]
selected_data = [None,None,None,None]
selectedImportantGraph = None
selectedPreviousImportantGraph = None
timeFrame_column_names = []
sectors = []
selectedSectorsDefinitions = [None,None,None,None]

#List Elements
dataNames = ['Flow of Funds', 'Balance Sheet (Annual)', 'Balance Sheet (Monthly)']
importantGraphs = {'C.11.Portfolio Invesment: Net incurrence of liabilities(Million USD)': 'C.11.Portfolio Invesment: Net incurrence of liabilities(Million USD)',
                     'E.14.Official Reserves(Million USD)' : 'E.14.Official Reserves(Million USD)',
                      'C.11.Portfolio Invesment: Net incurrence of liabilities(Million USD)(Equity-Debt)' : ['C.11.1.Equity Securities(Million USD)', 'C.11.2.Debt Securities(Million USD)']}
predictionModes = ['Disable Forecast', 'Enable Forecast']

#Keep read function here so it only executes it ones and keep one list with all the data, don't end it, make copies of it for further work
path = os.path.dirname(os.path.realpath(__file__))
path = os.path.join(path, 'EVDSdata.xlsx')


def connectToDatabase():
    sqlEngine = create_engine('postgresql+psycopg2://postgres:CT1SEr.FtW@database-1.cczlh6s4kbhf.us-east-1.rds.amazonaws.com/data')
    dbConnection = sqlEngine.connect()

def fillDefinitions():
    global selectedSectorsDefinitions
    for i in range(len(selectedSectors)):
        s =  selectedSectors[i]
        if(s!=None):
            s = s.split('.')[-1]
            if "(Thousand TRY)" in s: 
                s = s.replace('(Thousand TRY)', '')
            
            try:
                selectedSectorsDefinitions[i] = wikipedia.summary(s, sentences=2)
            except:
                selectedSectorsDefinitions[i] = "Definition not available"

def handleDataSourceGraphRequest(request):
    global selectedPreviousDataName, selectedDataName, a

    selectedPreviousDataName = selectedDataName
    selectedDataName = request.GET.get('datas')

    if selectedDataName != None:
        if selectedDataName != selectedPreviousDataName:
            if selectedDataName == dataNames[0]:
                a = pd.read_excel(path)
            elif selectedDataName == dataNames[1]:
                a = DataRetrieve.DataRetriever.retrieveAnnuallyData()
            elif selectedDataName == dataNames[2]:
                a = DataRetrieve.DataRetriever.retrieveMonthlyData()
    else:
        selectedDataName = dataNames[0]
        a = pd.read_excel(path)
        DataRetrieve.DataRetriever.push("asd","asd")

    
    
def handleImportantGraphRequest(request):
    global selectedPreviousImportantGraph, selectedImportantGraph

    selectedPreviousImportantGraph = selectedImportantGraph
    selectedImportantGraph = request.GET.get('importantGraph')

    if selectedImportantGraph != None:
        selectedDataName = dataNames[1]
        a = DataRetrieve.DataRetriever.retrieveAnnuallyData()

    if selectedImportantGraph == list(importantGraphs)[0]  or selectedImportantGraph == list(importantGraphs)[1]:
        counterSector = 1
        counterSectorArray = [counterSector]
    elif selectedImportantGraph == list(importantGraphs)[2]:
        counterSector = 2
        counterSectorArray = [1, 2]

def handleCustomGraphRequest(request):
    global a, selectedImportantGraph, columnsList, valuesList

    if (request.GET.get('saveCustom') != None):
        customSector1Name = request.GET.get('sectors1custom')
        customSector2Name = request.GET.get('sectors2custom')
        operator = request.GET.get('operatorCustom')

        firstEntry = a[a['Entry'] == customSector1Name]
        firstEntryVals = firstEntry.drop(firstEntry.columns[[0, 1]], axis=1).values
        secondEntry = a[a['Entry'] == customSector2Name]
        secondEntryVals = secondEntry.drop(secondEntry.columns[[0, 1]], axis=1).values
        
        newEntry = ops_dictionary[operator](firstEntryVals, secondEntryVals)
        
        columnsList = (firstEntry.iloc[:,2:].columns).tolist()
        columnsList.insert(0,'Entry')
        columnsList.insert(0, 'Unnamed: 0')

        newEntryName = request.GET.get('inputEntryName')

        valuesList = newEntry.tolist()[0]
        valuesList.insert(0, newEntryName)
        valuesList.insert(0, 2)

        sumFrameVals = (pd.DataFrame(valuesList, index=[columnsList], columns=[len(a.index)]).T)
        sumFrameVals.columns = columnsList

        a = pd.concat([a,sumFrameVals])

def handlePredictionRequest(request):
    global selectedPredictionMode, predictionModes

    selectedPredictionMode = request.GET.get('makePredictions')
    if selectedPredictionMode != None:
        if selectedPredictionMode == predictionModes[0]:
            showPredictions = False
        elif selectedPredictionMode == predictionModes[1]:
            showPredictions = True

def handleAddRemoveSectorRequest(request):
    global counterSector

    #handling button requests addSector-removeSector
    if (request.GET.get('addSector') != None and request.is_ajax() == False):
        if (counterSector != 4):
            counterSector = counterSector + 1
            counterSectorArray.append(counterSector)
    if (request.GET.get('removeSector') != None and request.is_ajax() == False):
        if (counterSector != 1):
            counterSector = counterSector - 1
            counterSectorArray.pop()

def handleListingRequest(request):
    global selectedSectors, sectors

    selectedSectors[0] = sectors[0]

    for i in counterSectorArray:
        selectedSectors[i-1] = sectors[i]
        requestString = 'sectors' + str(i)

        if (request.GET.get(requestString) != None and selectedDataName == selectedPreviousDataName):
            selectedSectors[i-1] = request.GET.get(requestString)

        if selectedImportantGraph != None:
            if selectedImportantGraph != list(importantGraphs)[2]:
                selectedSectors[i-1] = selectedImportantGraph
            else:
                selectedSectors[i-1] = importantGraphs.get(selectedImportantGraph)[i-1]
            if selectedImportantGraph == selectedPreviousImportantGraph:
                selectedSectors[i-1] = request.GET.get(requestString)
        

        selected_data[i-1] = a[a['Entry'] == selectedSectors[i-1]]
        selected_data[i-1].drop(selected_data[i-1].columns[[0, 1]], axis=1, inplace=True)


@csrf_exempt
def home(request, copy=None):
    global timeFrame_column_names, sectors

    handleDataSourceGraphRequest(request)
    handleImportantGraphRequest(request)
    handleCustomGraphRequest(request)
    handlePredictionRequest(request)
    handleAddRemoveSectorRequest(request)

    timeFrame_column_names = a.columns[a.columns.str.startswith('20')]
    sectors =  a[a.columns[1]]

    handleListingRequest(request)

    def getParams(chartType):
        if (chartType=='Line Plot' or chartType=='Scatter Plot' or chartType=='Stacked Bar Chart' or chartType == 'Area Graph' or chartType == 'Density Contour'):
            params = {'x':'years', 'y':'value','color':'variable'}
        elif (chartType=='Alluvial Diagram'):
            params = {'color':'value', 'color_continuous_scale':px.colors.sequential.Inferno}
        elif (chartType == 'Heat Map'):
            params = {'x':'years', 'y':'value'}
        elif (chartType == 'Grouped Bar Chart'):
            params = {'x':'years', 'y':'value','color':'variable', 'barmode':'group'} 
        return params

    def makePredictions(sectorsData):
        #filtering data
        dates = sectorsData['years']
        futureStepsN = 10
        forecastDates = []
        lastDate = dates[-1]

        for i in range(futureStepsN):
            lastDate = lastDate + datetime.timedelta(days=91)
            forecastDates.append(lastDate)
        
        forecastDates = pd.to_datetime(forecastDates)
        sectorsData['years'] = sectorsData['years'].append(forecastDates)
        
        for i in counterSectorArray:
            sectorName = 'Sector ' + str(i)
            values = sectorsData[sectorName]

            #creating data frame
            data = pd.DataFrame(
                {'dates': dates,
                'values': values
                })

            data.set_index('dates', inplace=True)
            train = data
        
            seasonality_m=4

            if selectedDataName == dataNames[0]:
                seasonality_m=4
            elif selectedDataName == dataNames[1]:
                seasonality_m=1
            elif selectedDataName == dataNames[2]:
                seasonality_m=12

            arima = pm.auto_arima(train, seasonal=True, m=seasonality_m, error_action='ignore', trace=True,
                                suppress_warnings=True, maxiter=10)
            
            forecastValues = arima.predict(futureStepsN)
            
            forecast_data = pd.Series(forecastValues, index = forecastDates) 

            sectorsData[sectorName] = sectorsData[sectorName].append(forecast_data)

        return sectorsData

    def drawChart(chartType):
        x = pd.to_datetime(timeFrame_column_names)
        data = {'years': x}

        for i in counterSectorArray:
            sectorName = 'Sector ' + str(i)
            y = selected_data[i-1].iloc[0]
            y.index = x
            data[sectorName] = y

        if (showPredictions):
            data = makePredictions(data)

        df= (pd.DataFrame.from_dict(data,orient='index').transpose()).melt(id_vars="years")

        params = getParams(chartType)        

        fig = getattr(px, plotDictionary[chartType])(
                df,
                **params
            )

        fig.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)')

        plot_div = plot(fig, output_type='div', include_plotlyjs=False)

        fillDefinitions()

        return plot_div

    if request.GET.get('plots') is None:
        getSelectedPlot = drawChart(list(plotDictionary.keys())[0])
    else:
        getSelectedPlot = drawChart(request.GET.get('plots'))

    

    context = {
        'plot': getSelectedPlot,
        'sectors': sectors,

        'selectedSector1': selectedSectors[0],
        'selectedSector2': selectedSectors[1],
        'selectedSector3': selectedSectors[2],
        'selectedSector4': selectedSectors[3],
        'selectedSectors': selectedSectors,

        'counterSectorArray': counterSectorArray,
        'plotTypes': plotDictionary.keys(),
        'selectedPlot': request.GET.get('plots'),
        'dataNames': dataNames,
        'selectedDataName': selectedDataName,
        'importantGraphs': importantGraphs.keys(),
        'selectedImportantGraph': selectedImportantGraph,
        'selectedPredictionMode': selectedPredictionMode,

        'selectedSectorsDefinitions1': selectedSectorsDefinitions[0],
        'selectedSectorsDefinitions2': selectedSectorsDefinitions[1],
        'selectedSectorsDefinitions3': selectedSectorsDefinitions[2],
        'selectedSectorsDefinitions4': selectedSectorsDefinitions[3],
        'selectedSectorsDefinitions': selectedSectorsDefinitions
    }
    if request.is_ajax():
        context['sectors'] = sectors.tolist()
        context['plotTypes'] = list(plotDictionary.keys())
        context['importantGraphs'] = list(importantGraphs.keys())
        context['makePredictions'] = predictionModes

        return HttpResponse(json.dumps(context))
    else:
        return render(request, 'home/dashboard.html', context)