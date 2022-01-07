"""
lit-walk CLI
"""
import os
import sys
import datetime
import logging
from argparse import ArgumentParser
from lit.walk import LitWalk
from rich import print
from rich.padding import Padding
from rich.table import Table
from rich.console import Console

class LitCLI:
    def __init__(self):
        """Initializes a new LitCLI instance"""
        # rich console
        self.console = Console()

        cmd = self._get_cmd()

        self._setup_logger()

        # initialize lit
        self.lit = LitWalk(self.verbose)

        self._logger.info("Initializing lit-walk...")

        getattr(self, cmd)()

    def _get_cmd(self):
        """
        Parses command line arguments and determine command to run + any global
        arguments.

        Based on: https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
        """
        parser = ArgumentParser(
            description="Tools to help with understanding the scientific literature",
            usage='''lit <command> [<args>]

List of supported commands:
   add      Adds a .bib BibTeX reference collection
   info     Display lit collection info
   list     Lists articles in users collection
   walk     Randomly suggests an article for review
   stats    [NOT IMPLEMENTED] Display user review stats
''')

        parser.add_argument('command', help='Sub-command to run')

        parser.add_argument(
            "--verbose",
            help="If enabled, prints verbose output",
            action="store_true",
        )
        
        # parse and validate sub-command
        #args = parser.parse_args(sys.argv[1:])

        args, unknown = parser.parse_known_args()

        # set logging verbosity
        self.verbose = args.verbose

        valid_cmds = ['add', 'info', 'list', 'stats', 'walk']

        if args.command not in valid_cmds:
            print(f"[ERROR] Unrecognized command specified: {args.command}!")
            parser.print_help()
            sys.exit()

        # execute method with same name as sub-command
        return args.command

    def _setup_logger(self):
        """Sets up logger to print messages to STDOUT"""
        logging.basicConfig(stream=sys.stdout, 
                            format='[%(levelname)s] %(message)s')

        self._logger = logging.getLogger('lit')

        if self.verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.WARN)


    def add(self):
        """
        "add" command
        """
        parser = ArgumentParser(description='Add a .bib BibTeX reference collection')

        parser.add_argument(
            "bibtex",
            nargs="?",
            type=str,
            help="Path to .bib file to be imported",
        )

        parser.add_argument(
            "--skip-check",
            help="If enabled, skips check for existing articles",
            action="store_true",
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        # check specified path
        if not os.path.exists(args.bibtex):
            raise Exception("No Bibtex file found at specified path!")
        elif not args.bibtex.endswith(".bib"):
            raise Exception("Invalid input! Expecting a .bib file...")

        # import and add any new entries to db
        self.lit.import_bibtex(args.bibtex, skip_check=args.skip_check)

    def list(self):
        """
        "list" command
        """
        # parse "walk"-specific args
        parser = ArgumentParser(description='Lists articles in users collection')

        parser.add_argument(
            "-n",
            "--num-articles",
            help="Maximum number of results to show",
            default=5,
            type=int
        )

        # - [ ] TODO
        #  parser.add_argument(
        #      "-d",
        #      "--details",
        #      help="If enabled, prints detailed views for each article",
        #      action="store_true",
        #  )

        parser.add_argument(
            "--missing-abstract",
            help="Only short articles which are missing abstracts",
            action="store_true"
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        articles = self.lit.get_articles(args.num_articles, args.missing_abstract)

        # order results by year
        articles.sort(key=lambda x: x['year'], reverse=True)

        self._print_header()
        
        table = Table(title=f"Articles (n={args.num_articles})")

        table.add_column("DOI", justify="left", style="sea_green1", no_wrap=True)
        table.add_column("Year", style="light_goldenrod3")
        table.add_column("Title", style="bold light_coral")

        for article in articles:
            table.add_row(article['doi'], str(article['year']), article['title'])

        self.console.print(table)

    def walk(self):
        """
        "walk" command
        """
        # parse "walk"-specific args
        parser = ArgumentParser(description='Randomly suggests an article for review')

        parser.add_argument(
            "-s",
            "--search",
            help="Limit search to articles containing the specified search phrase",
            default="",
            type=str
        )

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        res = self.lit.walk(args.search)

        article = res['article']

        self._print_header()

        if args.search != "":
            print(f"[sky_blue1]Including {res['num_filtered']}/{res['num_articles']} articles...[/sky_blue1]")
        
        year_str = f"[light_goldenrod3]{article['year']}[/light_goldenrod3]"
        print(f"[bold light_coral]{article['title']}[/bold light_coral] ({year_str})")

        if article['abstract'] is not None:
            print(Padding(article['abstract'], (1, 1), style='grey89'))

        print(f"[sea_green1] - url[/sea_green1]: {article['url']}")
        print(f"[sea_green1] - doi[/sea_green1]: {article['doi']}")

    def _print_header(self):
        """
        prints lit-walk header
        """
        print("[cyan]========================================[/cyan]")
        print(":books:", "[bold orchid]lit-walk[/bold orchid]")
        print("[cyan]========================================[/cyan]")

    def info(self):
        """
        "info" command
        """
        parser = ArgumentParser(description='Display lit collection info')

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])

        info = self.lit.info()

        self._print_header()
        print(f"[sky_blue1]# Articles[/sky_blue1]: {info['num_articles']}")
        print(f"[salmon1]Incomplete Metadata[/salmon1]:")
        print(f"[light_salmon1]- Missing \"DOI\":[/light_salmon1]: {info['missing']['doi']}")
        print(f"[light_salmon1]- Missing \"abstract\":[/light_salmon1]: {info['missing']['abstract']}")
        print(f"[light_salmon1]- Missing \"keywords\":[/light_salmon1]: {info['missing']['keywords']}")

    def stats(self):
        """
        "stats" command
        """
        # parse "stats"-specific args
        parser = ArgumentParser(description='Display user stats')

        # parse remaining parts of command args
        args = parser.parse_args(sys.argv[2:])
