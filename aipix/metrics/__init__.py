def influx(schema,metrics,tags={}):
	if tags:
		print("{0},{1} {2}".format(schema,
			','.join('{}={}'.format(key, value) for key, value in tags.items()),
			','.join('{}={}'.format(key, value) for key, value in metrics.items())))
	else:
		print("{0} {1}".format(schema,','.join('{}={}'.format(key, value) for key, value in metrics.items())))
