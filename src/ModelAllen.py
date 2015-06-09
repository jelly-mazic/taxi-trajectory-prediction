import csv
import numpy as np
import json
import sys
import argparse
from multiprocessing import Pool
import time

def main(args):
	timePoint1 = time.time()
	parser = argparse.ArgumentParser()
	parser.add_argument("-t", type = str, default = './train.csv')
	parser.add_argument("-i", type = str, default = './test.csv')
	parser.add_argument("-o", type = str, default = './ans.csv')
	parser.add_argument("-d",type = int, default = 3)
	parser.add_argument("-e",type = float, default = 0.01)

	args = parser.parse_args(args)
	
	global trainFile
	trainFile = args.t
	global testFile
	testFile = args.i
	global output
	output = args.o
	global digits
	digits = args.d
	global errorThreshold
	errorThreshold = args.d

	global polylines
	polylines = []
	global testPolylineData
	testPolylineData = []
	global metadata
	metadata = []
	global testMetadata
	testMetadata = []
	global destinations
	destinations = []


	trajectoryFile = csv.reader(open(trainFile,'r'))
	for trajectoryData in trajectoryFile:
		if len(trajectoryData[-1])>26:
			metadata.append(trajectoryData[:-1])

			polyline = np.around(json.loads(trajectoryData[-1]),digits)
			errorHappen = False
			for nodeNum in range(len(polyline)-1): #remove GPS error(error1)
				if np.linalg.norm(polyline[nodeNum]-polyline[nodeNum+1])>0.01:
					errorHappen = True
					break

			if errorHappen is False: #remove cycle polylines(error2)
				midPoint = polyline[len(polyline)/2]
				if (np.dot((midPoint-polyline[0]),(polyline[-1]-midPoint)) < 0): errorHappen = True

			if errorHappen is True: polylines.append(polyline)
	testTrajectoryFile = csv.reader(open(testFile,'r'))
	next(testTrajectoryFile)
	for testFileLine in testTrajectoryFile:
		testMetadata.append(testFileLine[:-1])
		testPolylineData.append(np.around(json.loads(testFileLine[-1]),digits))
	timePoint2 = time.time()
	setDestination()
	timePoint3 = time.time()
	buildAnswerFile()
	timePoint4 = time.time()
	print timePoint2 - timePoint1
	print timePoint3 - timePoint2
	print timePoint4 - timePoint3

def buildAnswerFile():
	File = open(output,'w')
	File.write('TRIP_ID'+','+'LATITUDE'+','+'LONGITUDE'+'\n')
	p = Pool()
	answer = p.map(BayesMethod,testPolylineData)
	for ans in xrange(len(answer)):
		File.write(str(testMetadata[ans][0]) + ',' + str(answer[ans][1]) + ',' + str(answer[ans][0]) + '\n')	
	File.close
"""
def buildAnswerFile():
	File = open(output,'w')
	File.write('TRIP_ID'+','+'LATITUDE'+','+'LONGITUDE'+'\n')
	for ans in xrange(len(testPolylineData)):
		answer = BayesMethod(testPolylineData[ans])
		File.write(str(testMetadata[ans][0]) + ',' + str(answer[1]) + ',' + str(answer[0]) + '\n')
	File.close
"""
def setDestination(): #(coordinate of the destinations,prob to reach this destinations,which polylines reach this destinations)
	for polylineNum in xrange(len(polylines)):
		isNew = True
		for destinationNum in xrange(len(destinations)):
			if (destinations[destinationNum][0] == polylines[polylineNum][-1]).all():
				destinations[destinationNum][1].append(polylineNum)
				isNew = False
				break
		if isNew == True: destinations.append([polylines[polylineNum][-1],[polylineNum]])

def BayesMethod(testPolylineData):
	scoreList = range(len(destinations))
	polylineSimilarityScore = polylineSimilarityScoring(testPolylineData)
	#callTypeScore = callTypeScoring(testMetadata)
	#dayTypescore = dayTypeScoring(testMetadata)
	#timeStampScore = timeStampScoring(testMetadata)
	for destinationNum in xrange(len(destinations)):
			sumOfpolylineSimilarityScore = 0
			#sumOfCallTypeScore = 0
			#sumOfDayTypeScore = 0
			#sumOfTimeStampScore = 0
			for trajectoryNum in destinations[destinationNum][1]:		
				sumOfpolylineSimilarityScore += polylineSimilarityScore[trajectoryNum]
				#sumOfCallTypeScore += callTypeScore[trajectoryNum]
				#sumOfDayTypeScore += dayTypescore[trajectoryNum]
				#sumOfTimeStampScore += timeStampScore[trajectoryNum]
			scoreList[destinationNum] = sumOfpolylineSimilarityScore
			#scoreList[destinationNum] = sumOfpolylineSimilarityScore+sumOfCallTypeScore+sumOfDayTypeScore+sumOfTimeStampScore
	return destinations[scoreList.index(max(scoreList))][0]

def polylineSimilarityScoring(testPolylineData):
	polylineSimilarityScore = [0]*len(polylines) #matchAmount is propotional to bayesian probability
	for polylineNum in xrange(len(polylines)):
		if np.dot((testPolylineData[-1]-testPolylineData[0]),(polylines[polylineNum][-1]-polylines[polylineNum][0]))<=0: polylineSimilarityScore[polylineNum] = 0 #train polyline must go the same way with test polyline
		elif np.dot((testPolylineData[-1]-testPolylineData[0]),(polylines[polylineNum][0]-testPolylineData[0]))<=0: polylineSimilarityScore[polylineNum] = 0 #destination must be on the way of test polyline
		else: polylineSimilarityScore[polylineNum] = len(list(node for node in testPolylineData if node in polylines[polylineNum]))/float(len(polylines[polylineNum]))
	#sumOfScore = sum(polylineSimilarityScore)
	return polylineSimilarityScore


"""
def timeStampScoring(testMetadata):
	timeStampScore = [0]*len(polylines)
	for metadataNum in xrange(len(metadata)):
		timeStampScore[metadataNum] = 1.0/(int(testMetadata[5])-int(metadata[metadataNum][5]))
	sumOfScore = sum(timeStampScore)
	if sumOfScore == 0: sumOfScore = 0.0000001
	for scoreNum in xrange(len(timeStampScore)): timeStampScore[scoreNum]/sumOfScore
	return timeStampScore

def callTypeScoring(testMetadata):
	CallTypeSimilarityScore = [0]*len(polylines)
	if testMetadata[1] == 'A':
		for metadataNum in xrange(len(metadata)):
			if metadata[metadataNum][1] == 'A': CallTypeSimilarityScore[metadataNum] += 1
	elif testMetadata[1] == 'B':
		for metadataNum in xrange(len(metadata)):
			if metadata[metadataNum][1] == 'B': CallTypeSimilarityScore[metadataNum] += 1
			if metadata[metadataNum][3] == testMetadata[3]: CallTypeSimilarityScore[metadataNum] += 2
	elif testMetadata[1] == 'C':
		for metadataNum in xrange(len(metadata)):
			if metadata[metadataNum][1] == 'C': CallTypeSimilarityScore[metadataNum] += 1
	sumOfScore = sum(CallTypeSimilarityScore)
	if sumOfScore == 0: sumOfScore = 0.0000001
	for scoreNum in xrange(len(CallTypeSimilarityScore)): CallTypeSimilarityScore[scoreNum]/sumOfScore
	return CallTypeSimilarityScore

def dayTypeScoring(testMetadata):
	dayTypeSimilarityScore = [0]*len(polylines)
	for metadataNum in xrange(len(metadata)):
		if metadata[metadataNum][6] == testMetadata[6]: dayTypeSimilarityScore[metadataNum] += 1
	sumOfScore = sum(dayTypeSimilarityScore)
	if sumOfScore == 0: sumOfScore = 0.0000001
	for scoreNum in xrange(len(dayTypeSimilarityScore)): dayTypeSimilarityScore[scoreNum]/sumOfScore
	return dayTypeSimilarityScore
"""

main(sys.argv[1:])