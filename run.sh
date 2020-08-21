#!/bin/bash

usage_error () { echo >&2 "$0: $1"; exit 2; }
assert_argument () { test "$1" != "$EOL" || usage_error "$2 requires an argument"; }
show_usage () { echo "Usage: $0 [-h] -o FILE -t TABLE [-a | -w] [-b | -n]"; }
show_help () {
	show_usage
	echo 
	echo 'Calls both scan.py and book.py conveniently.'
	echo
	echo 'Positional arguments:'
	echo '    -h, --help                Shows this help message.'
	echo '    -o FILE, --output FILE    Sets the output database.'
	echo '    -t TABLE, --table TABLE   Sets the output table name.'
	echo 
	echo 'Optional arguments:'
	echo '    -a, --auto                Automatically scans the codes. Is the default.'
	echo '    -w, --wait-for-enter      Waits for Enter key pressed before scanning.'
	echo '    -b, --start-background    Starts the background task of reading ISBNs from stdin.'
	echo '    -n, --no-background       Does not start the background task. Is the default.'
}
exit_prog () { 
	trap 'trapped' SIGINT
	if [ "$(lsof /tmp/scan.py.log)" ]; then
		kill -KILL $(lsof /tmp/scan.py.log | awk '{print $2}' | sed -n 2p)
	fi
	exit 0
}

trapped () { trap trapped SIGINT; }

EOL=$(echo '\01\03\03\07')
if [ "$#" != 0 ]; then
	set -- "$@" "$EOL"
	while [ "$1" != "$EOL" ]; do
		opt="$1"; shift
		case "$opt" in
			-h|--help)   show_help; exit 0;;
			-o|--output) assert_argument "$1" $opt; output="$1"; shift;;
			-t|--table)  assert_argument "$1" $opt; table="$1"; shift;;
			-b|--start-background) 
				test -v nobg && show_usage && usage_error 'argument -b/--start-background not allowed with -n/--no-background'
				test -v runbg && show_usage && usage_error 'argument -b/--start-background specified more than once'
				runbg='y';;
			-n|--no-background) 
				test -v runbg && show_usage && usage_error 'argument -n/--no-background not allowed with -b/--start-background'
				test -v nobg && show_usage && usage_error 'argument -n/--no-background specified more than once'
				nobg='y';;
			-a|--auto)
				test -v auto && show_usage && usage_error 'argument -a/--auto specified more than once'
				test -v wait_enter && show_usage && usage_error 'argument -a/auto not allowed with -w/--wait-for-enter'
				auto='y';;
			-w|--wait-for-enter)
				test -v wait_enter && show_usage && usage_error 'argument -w/--wait-for-enter specified more than once'
				test -v auto && show_usage && usage_error 'argument -w/--wait-for-enter not allowed with -a/auto'
				wait_for_enter='y';;

			-|''|[^-]*) set -- "$@" "$opt";;                                          # positional argument, rotate to the end
			--*=*)      set -- "${opt%%=*}" "${opt#*=}" "$@";;                        # convert '--name=arg' to '--name' 'arg'
			-[^-]?*)    set -- $(echo "${opt#-}" | sed 's/\(.\)/ -\1/g') "$@";;	      # convert '-abc' to '-a' '-b' '-c'
			--)		    while [ "$1" != "$EOL" ]; do set -- "$@" "$1"; shift; done;;  # process remaining arguments as positional
			-*)         usage_error "unknown option: '$opt'";;                        # catch misspelled options
			*)          usage_error "this should NEVER happen ($opt)";;               # sanity test for previous patterns
		esac
	done
	shift
fi

test ! -v output && show_usage && usage_error 'output database file not specified'
test ! -v table && show_usage && usage_error 'output table not specified'
[[ "$table" =~ / ]] && usage_error 'invalid character in table name: "/"'
test ! -e scan.py && usage_error 'scan.py not found'
test ! -e book.py && usage_error 'book.py not found'
test -v auto -o ! -v wait_enter && arg='-a'
test -v wait_enter && arg='-w'
test -v nobg -o ! -v runbg && arg2="$arg -n"
test -v runbg && arg2="$arg -b"
test ! -v arg && usage_error 'WHAT??!'
trap exit_prog SIGINT
test -e /dev/shm/tmp.db && rm /dev/shm/tmp.db
python3 scan.py ${arg}o DB:/dev/shm/tmp.db 2>/tmp/scan.py.log &
python3 book.py ${arg2}i DB:/dev/shm/tmp.db/barcodes -o DB:${output}/${table}

