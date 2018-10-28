import argparse
from datetime import datetime
import csv

import pdfplumber


# headers in the PDF that we'll target
INCOLS = ['COUNTY', 'GENDER', 'ACN', 'APV', 'DEM',
          'GRN', 'LBR', 'REP', 'UAF', 'UNI']

# headers for the CSV
OUTCOLS = ['report_date', 'county', 'gender', 'party', 'returned_votes']


def table_parser(table):
    '''
    given a table from a PDFplumber page -- a list of lists with every
    data point for a county and gender total in a single row -- melt
    into a tidy list of dictionaries with keys that match `OUTCOLS` above
    '''

    # list to dump data into
    outlist = []

    # placeholder value for county, which will be updated as we iterate
    county = None

    # loop over the rows in the table
    for row in table:

        # skip the headers
        if 'COUNTY' in row[0]:
            continue

        # if there is a value in the first cell, it's the name
        # of the county, so we need to update the placeholder value
        if row[0]:
            county = row[0]

        # gender is in the second cell
        gender = row[1]

        # now we can chop up the row -- which lists totals for this county and
        # this gender for every party -- into several lists, one for each
        # party

        # first, loop over the list of columns in the PDF data
        for i, col in enumerate(INCOLS):

            # skip county and gender
            if col.upper() in ['COUNTY', 'GENDER']:
                continue
            else:

                # the name of the party is wherever we're at in the list of
                # PDF columns -- 'ACN', 'APV', etc.
                party = col

                # using the index value (`i`) for the PDF columns we're
                # iterating over, grab the associated value out of the
                # `row` of data we're working on ... while we're at it,
                # kill out commas and coerce to integer
                count = int(row[i].replace(',', ''))

                # turn the whole thing into a dictionary by marrying
                # the list of data to the CSV columns defined in the
                # `OUTCOLS` variable above
                record = dict(zip(OUTCOLS, [report_date, county, gender,
                                            party, count]))

                # drop it into the outlist
                outlist.append(record)

    # return the data list
    return outlist


if __name__ == '__main__':

    # load up that parser, baby
    parser = argparse.ArgumentParser()

    # add the one positional argument
    parser.add_argument('--pdf', help='Path to CO early vote totals PDF')
    args = parser.parse_args()

    # get reference to the PDF
    pdf_in = args.pdf

    # assuming a common filename structure, e.g.
    # '20181026BallotsReturnedByAgePartyGender.pdf'
    # pull out the date
    rawdate = pdf_in.split('/')[-1].split('Ballot')[0]
    report_date = datetime.strptime(rawdate, '%Y%m%d').date().isoformat()

    # name the CSV file to write to
    csv_out = '{}-co-early-vote-totals.csv'.format(report_date)

    # open the PDF file and the CSV to write to
    with pdfplumber.open(args.pdf) as pdf, open(csv_out, 'w') as outfile:

        # create a writer object
        writer = csv.DictWriter(outfile, fieldnames=OUTCOLS)

        # write out the headers
        writer.writeheader()

        # create an empty list to dump clean data into
        early_voting_data = []

        # loop over the pages in the PDF
        for page in pdf.pages:

            # grab the table on the page
            table = page.extract_table()

            # the two tables on page 1 actually come in as one table,
            # so you need to chop out the bits from the summary table
            if page.page_number == 1:

                # a placeholder to grab the spot where the ~real~ table
                # starts
                starting_idx = None

                # loop over the table
                for i, row in enumerate(table):

                    # if we get to the line with 'COUNTY' up front,
                    # we're there, so stop
                    if 'COUNTY' in row[0]:
                        starting_idx = i
                        break

                # now we can redefine our table as everything from
                # that point onward
                table = table[starting_idx:]

            # lots going on here!
            # x[:-1] means leave off the 'Grand Total' value at the end
            # of every line in the PDF -- also, we're gonna skip the
            # useless "Voter Party" lines at the top of each table,
            # and we'll also skip the county summaries that pop up
            # every four lines or so
            clean_table = [x[:-1] for x in table if x and 'VOTER\xa0PARTY'
                           not in x[0] and 'TOTAL' not in x[0].upper()]

            # pop this into the our list above
            early_voting_data.extend(clean_table)

        # parse the data using the function defined above
        parsed_data = table_parser(early_voting_data)

        # write the contents to file
        writer.writerows(parsed_data)
