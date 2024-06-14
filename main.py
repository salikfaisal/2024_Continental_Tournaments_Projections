import sys
import random
import statistics
from bs4 import BeautifulSoup
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# finds the local file for your computer for the webdriver
# this is commented out because it is not needed after one run and is different for every user
#sys.path.append('C:\\Users\\ppp\\Selenium\\chromedriver_win32\\chromedriver.exe')

# gets the website where the elo ratings are located
driver.get('http://www.eloratings.net/')
# waits 10 seconds for the website to load
driver.implicitly_wait(10)

# uses XPath to scrape data
odd_ranked_teams = driver.find_elements(By.XPATH,
                                        "//div[@id='main']/div[@id='maindiv']/div[@id='maintable_World']/div[@class='slick-viewport']/div[@class='grid-canvas']/div[@class='ui-widget-content slick-row even']")
even_ranked_teams = driver.find_elements(By.XPATH,
                                         "//div[@id='main']/div[@id='maindiv']/div[@id='maintable_World']/div[@class='slick-viewport']/div[@class='grid-canvas']/div[@class='ui-widget-content slick-row odd']")
# Translates HTML to text and stores national elo ratings into a dictionary
team_elo_ratings = {}
for team in odd_ranked_teams:
    widget_content = team.text.split()
    country_name = ''
    for column_num, column in enumerate(widget_content):
        if column_num > 0 and column.isnumeric():
            team_rating = int(column)
            words_in_country_name = widget_content[1:column_num]
            country_name = ' '.join(words_in_country_name)
            team_elo_ratings.update({country_name: team_rating})
            break
for team in even_ranked_teams:
    widget_content = team.text.split()
    country_name = ''
    for column_num, column in enumerate(widget_content):
        if column_num > 0 and column.isnumeric():
            team_rating = int(column)
            words_in_country_name = widget_content[1:column_num]
            country_name = ' '.join(words_in_country_name)
            team_elo_ratings.update({country_name: team_rating})
            break
driver.quit()

# gets SPI ratings from ESPN/FiveThirtyEight
url = 'https://projects.fivethirtyeight.com/soccer-api/international/spi_global_rankings_intl.csv'
spi_data = requests.get(url).text.split(',')[6:]
spi_dict = {}

# changes SPi names to elo names if conflicting
spi_to_elo_change = {'USA': 'United States', 'Bosnia and Herzegovina': 'Bosnia/Herzegovina',
                     'United Arab Emirates': 'UAE', 'Swaziland': 'Eswatini', 'Antigua and Barbuda': 'Antigua & Barbuda',
                     'Sao Tome and Principe': 'São Tomé & Príncipe',
                     'St. Vincent and the Grenadines': 'St Vincent/Gren', 'Chinese Taipei': 'Taiwan',
                     'Timor-Leste': 'East Timor', 'Czech Republic': 'Czechia', 'Rep of Ireland': 'Ireland',
                     'Cape Verde Islands': 'Cape Verde', 'China PR': 'China', 'Congo DR': 'DR Congo',
                     'Curacao': 'Curaçao', 'Central African Republic': 'Central African Rep',
                     'St. Kitts and Nevis': 'Saint Kitts and Nevis', 'St. Lucia': 'Saint Lucia',
                     'St. Martin': 'Saint Martin', 'Turks and Caicos Islands': 'Turks and Caicos', 'Macau': 'Macao'
                     }
for item_num, item in enumerate(spi_data):
    if item_num % 5 == 0:
        rating = float(spi_data[item_num + 4].split()[0])
        elo_adjusted_rating = 1000 + 10 * rating
        if item in spi_to_elo_change:
            item = spi_to_elo_change[item]
        spi_dict.update({item: elo_adjusted_rating})

# combines SPI and world elo ratings
for team, elo_rating in team_elo_ratings.items():
    if team in ['Northern Cyprus', 'Kurdistan', 'Réunion', 'Saint Barthélemy', 'Wallis and Futuna', 'Vatican',
                'Falkland Islands', 'Eastern Samoa', 'Palau', 'Mayotte', 'Somaliland', 'Western Sahara', 'Greenland',
                'Monaco', 'Chagos Islands', 'St Pierre & Miquelon', 'Tibet', 'FS Micronesia', 'Kiribati',
                'Northern Marianas', 'Niue', 'Sint Eustatius', 'Saba']:
        continue
        # this is because there is no SPI rating for these countries, and they are not officially FIFA members
    spi_elo = spi_dict[team]
    new_rating = (elo_rating + spi_elo) / 2
    team_elo_ratings.update({team: new_rating})

# This updates Germany and the United States elo rating to reflect its home advantage
team_elo_ratings['Germany'] += 100
team_elo_ratings['United States'] += 100


# this function returns a simulation of the results of a game given the elo ratings of the two teams
def match_result(team_1_elo, team_2_elo):
    # uses the elo formula to get the two-outcome win probability
    team_1_wl = 1 / (10 ** ((team_2_elo - team_1_elo) / 400) + 1)
    # gets the average goal difference expected between the two sides
    # if two sides have an equal rating the probabilities are: 35% Team 1 win, 30% draw, 35% Team 2 win
    team_1_margin_mean = statistics.NormalDist(0, 1.3).inv_cdf(team_1_wl)
    # the goal difference as a result of a random simulation
    team_1_margin = round(statistics.NormalDist(team_1_margin_mean, 1.3).inv_cdf(random.random()))
    # the goal probability distribution from 1826 matches in the 2020-21 season in Europe's top 5 leagues
    goal_prob = [0.25985761226725085, 0.3417305585980285, 0.22343921139101863, 0.1119934282584885, 0.0443592552026287,
                 0.014786418400876232, 0.0024644030668127055, 0.0008214676889375684, 0.0002738225629791895,
                 0.0002738225629791895]
    gp_list = []
    if abs(team_1_margin) > 9:
        winning_goal_count = abs(team_1_margin)
        losing_goal_count = 0
    else:
        gp_list = goal_prob[abs(team_1_margin):]
        total = sum(gp_list)
        cum = 0
        for goal_count, goal_probability in enumerate(gp_list):
            gp_list[goal_count] = goal_probability / total
        goal_result = random.random()
        for gc, gp in enumerate(gp_list):
            cum += gp
            if goal_result < cum:
                winning_goal_count = gc + abs(team_1_margin)
                winning_goal_count = gc + abs(team_1_margin)
                losing_goal_count = winning_goal_count - abs(team_1_margin)
                break
    if team_1_margin >= 0:
        home_goals = winning_goal_count
        away_goals = home_goals - team_1_margin
    else:
        away_goals = winning_goal_count
        home_goals = away_goals + team_1_margin
    return [home_goals, away_goals]


# Groups initialized
euro_groups = [['Germany', 'Scotland', 'Hungary', 'Switzerland'], ['Spain', 'Croatia', 'Italy', 'Albania'],
               ['Slovenia', 'Denmark', 'Serbia', 'England'], ['Poland', 'Netherlands', 'Austria', 'France'],
               ['Belgium', 'Slovakia', 'Romania', 'Ukraine'], ['Turkey', 'Georgia', 'Portugal', 'Czechia']]
copa_groups = [['Argentina', 'Peru', 'Chile', 'Canada'], ['Mexico', 'Ecuador', 'Venezuela', 'Jamaica'],
               ['United States', 'Uruguay', 'Panama', 'Bolivia'], ['Brazil', 'Colombia', 'Paraguay', 'Costa Rica']]

euro_summary = []
euro_group_summary = {}
copa_summary = []
copa_group_summary = {}

for group_number, group in enumerate(euro_groups):
    for team in group:
        euro_summary.append([team, 0, 0, 0, 0, 0, chr(65 + group_number)])
        euro_group_summary.update({team: [0, 0, 0, 0, 0, 0, 0, chr(65 + group_number)]})

for group_number, group in enumerate(copa_groups):
    for team in group:
        copa_summary.append([team, 0, 0, 0, 0, chr(65 + group_number)])
        copa_group_summary.update({team: [0, 0, 0, 0, 0, 0, 0, chr(65 + group_number)]})


# A class for functions used for the Group Stage
class group_stage:
    def __init__(self, group, euro):
        self.group = group
        self.euro = euro

    # This function returns a list of all the Group State matches already completed
    def matches_completed(self):
        if self.euro:
            matches_completed = []
        else:
            matches_completed = []

        return matches_completed

    # This function returns the various matchups within a particular group
    def group_matches(self):
        matches = []
        for team_1_pos, team_1 in enumerate(self.group):
            for team_2_pos, team_2 in enumerate(self.group):
                if team_1_pos < team_2_pos:
                    matches.append([team_1, team_2])
        return matches

    # This function returns the elo ratings for each team in a Group Stage match
    def match_ratings(self):
        matches = self.group_matches()
        ratings = []
        for match in matches:
            rating = []
            for team_number, team in enumerate(match):
                rating.append(team_elo_ratings[team])
            ratings.append(rating)
        return ratings

    # This function returns a final simulated group
    def group_simulation(self):
        table = {}
        group_ratings = self.match_ratings()
        matches_completed = self.matches_completed()
        for team in self.group:
            table.update({team: [0, 0, 0, 0]})
        match_results = []
        for match_number, match in enumerate(self.group_matches()):
            simulation_needed = True
            rating = group_ratings[match_number]
            team_1_standings = table[match[0]]
            team_2_standings = table[match[1]]
            for finished_match in matches_completed:
                # This checks to see if the match has already been played
                if match[0] in finished_match and match[1] in finished_match:
                    simulation_needed = False
                    if match[0] == finished_match[0]:
                        result = finished_match[2:]
                    else:
                        result = [finished_match[3], finished_match[2]]
                    break
            # This simulates the match if it has not been played yet
            if simulation_needed:
                result = match_result(rating[0], rating[1])
            match_results.append(result)
            # This updates the standings to reflect the match
            if result[0] > result[1]:
                team_1_standings[0] = team_1_standings[0] + 3
            elif result[0] == result[1]:
                team_1_standings[0] = team_1_standings[0] + 1
                team_2_standings[0] = team_2_standings[0] + 1
            else:
                team_2_standings[0] = team_2_standings[0] + 3
            team_1_standings[1] += result[0]
            team_2_standings[1] += result[1]
            team_1_standings[2] += result[1]
            team_2_standings[2] += result[0]
            team_1_standings[3] = team_1_standings[1] - team_1_standings[2]
            team_2_standings[3] = team_2_standings[1] - team_2_standings[2]
            table[match[0]] = team_1_standings
            table[match[1]] = team_2_standings
        standings = []
        for team in table:
            standing = [team]
            standing.extend(table[team])
            standings.append(standing)
        standings = sorted(standings, key=lambda data: (data[1], data[4], data[2]), reverse=True)
        return standings


# A class for functions used during the knockout stage
class knockout_stage:
    # This sets the matchups for the knockout stage based on the results of the Group Stage
    def __init__(self, group_winners, group_runners_up, third_place_teams, euro):
        self.euro = euro
        if euro:
            sequences = [['A', 'D', 'B', 'C'], ['A', 'E', 'B', 'C'], ['A', 'F', 'B', 'C'], ['D', 'E', 'A', 'B'],
                         ['D', 'F', 'A', 'B'], ['E', 'F', 'B', 'A'], ['E', 'D', 'C', 'A'], ['F', 'D', 'C', 'A'],
                         ['E', 'F', 'C', 'A'], ['E', 'F', 'D', 'A'], ['E', 'D', 'B', 'C'], ['F', 'D', 'C', 'B'],
                         ['F', 'E', 'C', 'B'], ['F', 'E', 'D', 'B'], ['F', 'E', 'D', 'C']
                         ]

            group_to_team_dict = {}
            for team in third_place_teams:
                group = euro_group_summary[team][-1]
                group_to_team_dict.update({group: team})

            for sequence in sequences:
                sequence_found = False
                for advancing_team_rank, group in enumerate(group_to_team_dict):
                    if group not in sequence:
                        break
                    elif advancing_team_rank == 3:
                        sequence_found = True
                if sequence_found:
                    ordered_sequence = []
                    for group in sequence:
                        ordered_sequence.append(group_to_team_dict[group])
                    break

            round_of_16_matchups = [[group_winners[1], ordered_sequence[0]], [group_winners[0], group_runners_up[2]],
                                    [group_winners[5], ordered_sequence[3]], [group_runners_up[3], group_runners_up[4]],
                                    [group_winners[4], ordered_sequence[2]], [group_winners[3], group_runners_up[5]],
                                    [group_winners[2], ordered_sequence[1]], [group_runners_up[0], group_runners_up[1]]]



            self.round_of_16_matchups = round_of_16_matchups
        else:
            quarterfinalists = [group_winners[0], group_runners_up[1], group_winners[1], group_runners_up[0],
                                group_winners[2], group_runners_up[3], group_winners[3], group_runners_up[2]]

            self.quarterfinalists = quarterfinalists

    # This returns the nations that advanced to the quarterfinals through simulations or returns the actual quarterfinalists
    # if the matches have been completed
    def round_of_16(self):
        if self.euro:
            r16_matchups = self.round_of_16_matchups
            quarterfinalists = []
            # The quarterfinalists have already been determined
            for match in r16_matchups:
                team_1_elo = team_elo_ratings[match[0]]
                team_2_elo = team_elo_ratings[match[1]]
                result = match_result(team_1_elo, team_2_elo)
                if result[0] > result[1]:
                    quarterfinalists.append(match[0])
                elif result[0] < result[1]:
                    quarterfinalists.append(match[1])
                else:
                    quarterfinalists.append(match[random.randrange(0, 2)])

            return quarterfinalists

    # This returns the nations that advanced to the quarterfinals and semifinals through simulations or returns the actual
    # quarterfinalists add semifinalists if the matches have been completed
    def quarterfinals(self):
        if self.euro:
            quarterfinalists = self.round_of_16()
        else:
            quarterfinalists = self.quarterfinalists
        semifinalists = []

        qf_matches = []
        qf_match = []
        for team in quarterfinalists:
            qf_match.append(team)
            if len(qf_match) == 2:
                qf_matches.append(qf_match)
                qf_match = []
        for match in qf_matches:
            team_1_elo = team_elo_ratings[match[0]]
            team_2_elo = team_elo_ratings[match[1]]
            result = match_result(team_1_elo, team_2_elo)
            if result[0] > result[1]:
                semifinalists.append(match[0])
            elif result[0] < result[1]:
                semifinalists.append(match[1])
            else:
                semifinalists.append(match[random.randrange(0, 2)])
        return quarterfinalists, semifinalists

    # This returns the nations that advanced to the quarterfinals, semifinals, and final through simulations or returns the actual
    # quarterfinalists, semifinalists, and finalists if the matches have been completed
    def semifinals(self):
        quarterfinalists, semifinalists = self.quarterfinals()
        finalists = []
        sf_matches = []
        sf_match = []
        for team in semifinalists:
            sf_match.append(team)
            if len(sf_match) == 2:
                sf_matches.append(sf_match)
                sf_match = []
        for match in sf_matches:
            team_1_elo = team_elo_ratings[match[0]]
            team_2_elo = team_elo_ratings[match[1]]
            result = match_result(team_1_elo, team_2_elo)
            if result[0] > result[1]:
                finalists.append(match[0])
            elif result[0] < result[1]:
                finalists.append(match[1])
            else:
                finalists.append(match[random.randrange(0, 2)])
        return quarterfinalists, semifinalists, finalists

    # This returns the nations that advanced to the quarterfinals, semifinals, final, and champion through simulations
    # or returns the actual quarterfinalists, semifinalists, finalists and champions if the matches have been completed
    def final(self):
        quarterfinalists, semifinalists, finalists = self.semifinals()
        team_1_elo = team_elo_ratings[finalists[0]]
        team_2_elo = team_elo_ratings[finalists[1]]
        result = match_result(team_1_elo, team_2_elo)
        if result[0] > result[1]:
            champion = finalists[0]
        elif result[0] < result[1]:
            champion = finalists[1]
        else:
            champion = finalists[random.randrange(0, 2)]
        return quarterfinalists, semifinalists, finalists, champion


# Simulates the World Cup 10,000 times and stores the information
for simulation in range(10000):
    group_winners = []
    group_runner_ups = []
    third_place_table = []
    # Simulates the Group Stage and stores data for each Group
    for group in euro_groups:
        group_sim = group_stage(group, True)
        group_sim_results = group_sim.group_simulation()
        for position, team in enumerate(group_sim_results):
            summary_info = euro_group_summary[team[0]]
            summary_info[0] += team[1]
            summary_info[1] += team[4]
            summary_info[position + 2] += 1
            summary_info[6] += (position + 1)
            euro_group_summary.update({team[0]: summary_info})
            if position == 0:
                group_winners.append(team[0])
            elif position == 1:
                group_runner_ups.append(team[0])
            elif position == 2:
                third_place_table.append(team)
    # gets third place teams advancing to the round of 16
    third_place_table = sorted(third_place_table, key=lambda data: (data[1], data[4], data[2]), reverse=True)
    third_place_table = third_place_table[0:4]
    third_place_advancing_teams = []
    for team_stats in third_place_table:
        third_place_advancing_teams.append(team_stats[0])
    # Reports Group Stage Results to Knockout Stage
    ks_sim = knockout_stage(group_winners, group_runner_ups, third_place_advancing_teams, True)
    # Simulates Knockout Stage
    quarterfinalists, semifinalists, finalists, champion = ks_sim.final()
    # Stores the results of the Knockout Stage
    for team in euro_summary:
        if team[0] == champion:
            team[1] += 1
            team[2] += 1
            team[3] += 1
            team[4] += 1
            team[5] += 1
        elif team[0] in finalists:
            team[1] += 1
            team[2] += 1
            team[3] += 1
            team[4] += 1
        elif team[0] in semifinalists:
            team[1] += 1
            team[2] += 1
            team[3] += 1
        elif team[0] in quarterfinalists:
            team[1] += 1
            team[2] += 1
        elif team[0] in group_winners or team[0] in group_runner_ups:
            team[1] += 1


    # Copa America
    # Simulates the Group Stage and stores data for each Group
    group_winners = []
    group_runner_ups = []
    for group in copa_groups:
        group_sim = group_stage(group, False)
        group_sim_results = group_sim.group_simulation()
        for position, team in enumerate(group_sim_results):
            summary_info = copa_group_summary[team[0]]
            summary_info[0] += team[1]
            summary_info[1] += team[4]
            summary_info[position + 2] += 1
            summary_info[6] += (position + 1)
            copa_group_summary.update({team[0]: summary_info})
            if position == 0:
                group_winners.append(team[0])
            elif position == 1:
                group_runner_ups.append(team[0])
    # Reports Group Stage Results to Knockout Stage
    ks_sim = knockout_stage(group_winners, group_runner_ups, [], False)
    # Simulates Knockout Stage
    quarterfinalists, semifinalists, finalists, champion = ks_sim.final()
    # Stores the results of the Knockout Stage
    for team in copa_summary:
        if team[0] == champion:
            team[1] += 1
            team[2] += 1
            team[3] += 1
            team[4] += 1
        elif team[0] in finalists:
            team[1] += 1
            team[2] += 1
            team[3] += 1
        elif team[0] in semifinalists:
            team[1] += 1
            team[2] += 1
        elif team[0] in quarterfinalists:
            team[1] += 1


euro_group_sim_summary = []
copa_group_sim_summary = []
for team, data in euro_group_summary.items():
    team_info = [team]
    team_info.extend(data)
    euro_group_sim_summary.append(team_info)

for team, data in copa_group_summary.items():
    team_info = [team]
    team_info.extend(data)
    copa_group_sim_summary.append(team_info)

euro_group_sim_summary = sorted(euro_group_sim_summary, key=lambda data: data[7])
euro_group_sim_summary = sorted(euro_group_sim_summary, key=lambda data: data[8])
euro_summary = sorted(euro_summary, key=lambda data: (data[5], data[4], data[3], data[2], data[1]), reverse=True)

copa_group_sim_summary = sorted(copa_group_sim_summary, key=lambda data: data[7])
copa_group_sim_summary = sorted(copa_group_sim_summary, key=lambda data: data[8])
copa_summary = sorted(copa_summary, key=lambda data: (data[4], data[3], data[2], data[1]), reverse=True)

line_format = '{pos:^4}|{team:^15}|{Avg_Pos:^10}|{Pts:^13}|{GD:^10}|{KS:^10}|{First:^7}|{Second:^7}|{Third:^7}|{Fourth:^7}|'
group_format = '{group:^100}'

for team_number, team_stats in enumerate(euro_group_sim_summary):
    if team_number % 4 == 0:
        print()
        group = 'Group ' + team_stats[8]
        print(group_format.format(group=group))
        print(line_format.format(pos='Pos', team='Team', Avg_Pos='Avg. Pos', Pts='Est. Points', GD='Est. GD', KS='Advance', First='1st',
                                 Second='2nd', Third='3rd', Fourth='4th'))
        print('-' * 100)
    position = team_number % 4 + 1
    team = team_stats[0]
    points = round(team_stats[1] / 10000, 2)
    gd = round(team_stats[2] / 10000, 2)
    advance = str(round((team_stats[3] + team_stats[4]) / 100)) + '%'
    first = str(round(team_stats[3] / 100)) + '%'
    second = str(round(team_stats[4] / 100)) + '%'
    third = str(round(team_stats[5] / 100)) + '%'
    fourth = str(round(team_stats[6] / 100)) + '%'
    avg_pos = round(team_stats[7] / 10000, 1)
    print(line_format.format(pos=position, team=team, Avg_Pos=avg_pos, Pts=points, GD=gd, KS=advance, First=first, Second=second,
                             Third=third,
                             Fourth=fourth))

print('\n\n')
for team_number, team_stats in enumerate(copa_group_sim_summary):
    if team_number % 4 == 0:
        print()
        group = 'Group ' + team_stats[8]
        print(group_format.format(group=group))
        print(line_format.format(pos='Pos', team='Team', Avg_Pos='Avg. Pos', Pts='Est. Points', GD='Est. GD',
                                 KS='Advance', First='1st',
                                 Second='2nd', Third='3rd', Fourth='4th'))
        print('-' * 100)
    position = team_number % 4 + 1
    team = team_stats[0]
    points = round(team_stats[1] / 10000, 2)
    gd = round(team_stats[2] / 10000, 2)
    advance = str(round((team_stats[3] + team_stats[4]) / 100)) + '%'
    first = str(round(team_stats[3] / 100)) + '%'
    second = str(round(team_stats[4] / 100)) + '%'
    third = str(round(team_stats[5] / 100)) + '%'
    fourth = str(round(team_stats[6] / 100)) + '%'
    avg_pos = round(team_stats[7] / 10000, 1)
    print(line_format.format(pos=position, team=team, Avg_Pos=avg_pos, Pts=points, GD=gd, KS=advance, First=first,
                             Second=second,
                             Third=third,
                             Fourth=fourth))

print()
print()
euro_format = '{title:^99}'
euro_line_format = '{Pos:^4}|{team:^15}|{R16:^15}|{QF:^18}|{SF:^12}|{F:^10}|{W:^18}|'
copa_format = '{title:^83}'
copa_line_format = '{Pos:^4}|{team:^15}|{QF:^18}|{SF:^12}|{F:^10}|{W:^18}|'



print(euro_format.format(title='UEFA Euro 2024 Forecast'))
print()
print(euro_line_format.format(Pos='Pos', team='Team', R16='Round of 16', QF='Quarterfinals', SF='Semifinals', F='Final',
                         W='Win Euros'))
print('-' * 99)
for rank, team_stats in enumerate(euro_summary):
    team = team_stats[0]
    make_r16 = str(round(team_stats[1] / 100)) + '%'
    make_qf = str(round(team_stats[2] / 100)) + '%'
    make_sf = str(round(team_stats[3] / 100)) + '%'
    make_final = str(round(team_stats[4] / 100)) + '%'
    win_euros = str(round(team_stats[5] / 100)) + '%'
    print(euro_line_format.format(Pos=rank + 1, team=team, R16=make_r16, QF=make_qf, SF=make_sf, F=make_final, W=win_euros))

# stores the data for the Group Stage in a Data Frame
for team_number, country in enumerate(euro_group_sim_summary):
    new_country_data = [country[-1]]
    position = team_number % 4 + 1
    new_country_data.append(position)
    new_country_data.append(country[0])
    for data in country[1: -1]:
        new_country_data.append(data / 10000)
    advance = new_country_data[5] + new_country_data[6]
    new_country_data.insert(5, advance)
    euro_group_sim_summary[team_number] = new_country_data

euro_group_df = pd.DataFrame(euro_group_sim_summary, columns=['Group', 'Group_Position', 'Team', 'Avg_Pos', 'Avg_Pts',
                                                              'Avg_GD', 'Advance', '1st', '2nd', '3rd', '4th'])

# stores the data for the Knockout Stage in a Data Frame
for team_number, country_data in enumerate(euro_summary):
    new_country_data = [team_number + 1, country_data[0], country_data[-1]]
    for data in country_data[1:-1]:
        new_country_data.append(data / 10000)
    euro_summary[team_number] = new_country_data

euro_ks_df = pd.DataFrame(euro_summary, columns=['Rank', 'Team', 'Group', 'Make_R16', 'Make_QF', 'Make_SF', 'Make_Final',
                                          'Win_Euros'])


# Copa America
print('\n\n')
print(copa_format.format(title='2024 Copa America Forecast'))
print()
print(copa_line_format.format(Pos='Pos', team='Team', QF='Quarterfinals', SF='Semifinals', F='Final',
                         W='Win Copa America'))
print('-' * 83)
for rank, team_stats in enumerate(copa_summary):
    team = team_stats[0]
    make_qf = str(round(team_stats[1] / 100)) + '%'
    make_sf = str(round(team_stats[2] / 100)) + '%'
    make_final = str(round(team_stats[3] / 100)) + '%'
    win_copa = str(round(team_stats[4] / 100)) + '%'
    print(copa_line_format.format(Pos=rank + 1, team=team, QF=make_qf, SF=make_sf, F=make_final, W=win_copa))

# stores the data for the Group Stage in a Data Frame
for team_number, country in enumerate(copa_group_sim_summary):
    new_country_data = [country[-1]]
    position = team_number % 4 + 1
    new_country_data.append(position)
    new_country_data.append(country[0])
    for data in country[1: -1]:
        new_country_data.append(data / 10000)
    advance = new_country_data[4] + new_country_data[5]
    new_country_data.insert(4, advance)
    copa_group_sim_summary[team_number] = new_country_data

copa_group_df = pd.DataFrame(copa_group_sim_summary, columns=['Group', 'Group_Position', 'Team', 'Avg_Pos', 'Avg_Pts',
                                                              'Avg_GD', 'Advance', '1st', '2nd', '3rd', '4th'])

# stores the data for the Knockout Stage in a Data Frame
for team_number, country_data in enumerate(copa_summary):
    new_country_data = [team_number + 1, country_data[0], country_data[-1]]
    for data in country_data[1:-1]:
        new_country_data.append(data / 10000)
    copa_summary[team_number] = new_country_data

copa_ks_df = pd.DataFrame(copa_summary, columns=['Rank', 'Team', 'Group', 'Make_QF', 'Make_SF', 'Make_Final',
                                          'Win_Copa_America'])

# exports Results to CSV files
euro_group_df.to_csv("Euros_Group_Stage_Forecast_Results.csv", index=False, header=True)
euro_ks_df.to_csv("Euros_Knockout_Stage_Forecast_Results.csv", index=False, header=True)

copa_group_df.to_csv("Copa_America_Group_Stage_Forecast_Results.csv", index=False, header=True)
copa_ks_df.to_csv("Copa_America_Knockout_Stage_Forecast_Results.csv", index=False, header=True)