accept = ":9000"
dial = ":9000"

server:
	sudo python3.6 -m serve_file --accept "$(accept)" --file c.txt --chunk-size 40

client:
	sudo python3.6 -m serve_file --dial "$(dial)" --file b.txt 
