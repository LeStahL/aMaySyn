name='drums'
synfile=$name'.syn'
tempfile=$name'.may.template'
destfile=$name'.may'
outfile=$name'.tmp'

rm 'out/'$name'_'*'.wav'

sed -i 's/#maindrum/maindrum/' $synfile
ndrums=$(grep maindrum $synfile | wc -l)

echo $ndrums drums in $synfile

for i in $(seq 1 $ndrums)
do

	sed 's/\$/'$i'/g' $tempfile > $destfile
	
	echo 'run '$synfile' with drum synth '$i
	./run.sh $name -headless > $outfile

	k=$(printf "%03d" $i)

	drumname=$(grep 'ACTUALLY USED DRUMS' $outfile | sed -e "s/.*\['//" -e "s/'\]//")
	# mv -v 'out/'$name'_001.wav' 'out/_'$name'_'$drumname'.wav'

done

###################
# UPCOMING IDEAS: #
################### 
#
# - different vel / aux
# - call template of randoms and store values
#
#
#
