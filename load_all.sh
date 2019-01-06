# call this after you changed something in the .may structure
#
# IMPORTANT: FIRST implement your change in the saveCSV() function
#            THEN  call this script and SAVE each .may
#            THEN  implement your change in the loadCSV() function

for i in *.may
	do
		./run.sh $(echo $i | sed 's/.may//')
	done
