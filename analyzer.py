class Analyzer:
    def __init__(self):
        print("Analyzer initialized")

    @staticmethod
    def check_player(playermon):
        player = playermon.split(":")[0]
        if "1" in player:
            player = 1
        else:
            player = 2
        return player

    @staticmethod
    def find_nicknames(data):
        nicknames = {}
        for line in data:
            if "|switch|" in line:
                nickname = line.split("|")[2]
                parts = nickname.split(":")
                nickname = parts[0][:-1] + ":" + parts[1]
                pokemon = line.split("|")[3].split(",")[0]
                nicknames[nickname] = pokemon
        return nicknames

    @staticmethod
    def find_playernames(data):
        players = []
        for line in data:
            if "|title|" in line:
                players = line.split("|")[2]
                players = players.split("vs.")
        return players[0][:-1], players[1][1:]

    def check_winner(self, data, players, singles=False):
        faints = []
        for line in data:
            if "|faint|" in line:
                faints.append(line)
        p1, p2 = (6, 6) if singles else (4, 4)
        for faint in faints:
            player = faint.split("|")[2]
            player = self.check_player(player)
            if player == 1:
                p1 -= 1
            else:
                p2 -= 1
        return self.winner_string(players, faints, p1, p2)

    @staticmethod
    def winner_string(players, faints, p1, p2):
        if p1 == 0:
            return players[1] + " won " + str(p2) + "-" + str(p1)
        elif p1 == 0 and p2 == 0:
            player = faints[-1].split(":")[0]
            player = player.split("|")[2]
            if "1" in player:
                return players[0] + " won " + str(p1) + "-" + str(p2)
            else:
                return players[1] + " won " + str(p2) + "-" + str(p1)
        else:
            return players[0] + " won " + str(p1) + "-" + str(p2)

    @staticmethod
    def init_kd(nicknames):
        kd = {}
        for nickname in nicknames.keys():
            kd[nickname] = [0, 0, 0]
        return kd

    @staticmethod
    def add_kill(kd, nickname_search, direct=False):
        mon_kd = kd[nickname_search]
        if direct:
            mon_kd[0] += 1
        else:
            mon_kd[1] += 1
        kd[nickname_search] = mon_kd
        return kd

    @staticmethod
    def nickname_marker(mon):
        parts = mon.split(":")
        nickname_search = parts[0][:-1] + ":" + parts[1]
        return nickname_search

    def analyze_replay(self, data, singles=False):
        nicknames = self.find_nicknames(data)
        kd = self.init_kd(nicknames)

        faints = []
        for i in range(len(data)):
            if "|faint|" in data[i]:
                faints.append((data[i], i))

        kills = []
        for faint in faints:
            mon = faint[0].split("|")[2]
            nickname_search = self.nickname_marker(mon)
            pokemon = nicknames[nickname_search]

            # add death count
            mon_kd = kd[nickname_search]
            mon_kd[2] += 1
            kd[nickname_search] = mon_kd

            # search killer and cause
            kd, kills = self.search_cause(data, faint, mon, pokemon, nicknames, kd, kills)

        match_analysis = self.summarize(data, kd, kills, nicknames, singles)
        return match_analysis

    def summarize(self, data, kd, kills, nicknames, singles=False):
        players = self.find_playernames(data)
        winner = self.check_winner(data, players, singles)
        p1_mons = []
        p2_mons = []
        for key in kd.keys():
            if "p1" in key:
                p1_mons.append((key, kd[key]))
            else:
                p2_mons.append((key, kd[key]))

        summary = "**Result:** ||" + winner + "||\n\n"
        summary = summary + "**" + players[0] + "**:\n||"
        for mon in p1_mons:
            summary = summary + nicknames[mon[0]] + " has " + str(mon[1][0]) + " direct kills, " + str(
                mon[1][1]) + " passive kills, and " + str(mon[1][2]) + " deaths. \n"
        summary = summary + "||\n"
        summary = summary + "**" + players[1] + "**:\n||"
        for mon in p2_mons:
            summary = summary + nicknames[mon[0]] + " has " + str(mon[1][0]) + " direct kills, " + str(
                mon[1][1]) + " passive kills, and " + str(mon[1][2]) + " deaths. \n"
        summary = summary + "||\n"
        summary = summary + "**Match Report:** \n||"
        for kill in kills:
            summary = summary + kill + "\n"
        summary = summary + "||"
        return summary

    def search_cause(self, data, faint, mon, pokemon, nicknames, kd, kills):
        n = faint[1]
        searching = True
        player = self.check_player(mon)
        kd, kills = self.check_direct(data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_direct(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        marker = "|-damage|" + mon + "|0 fnt"
        if marker in data[:n]:
            for i in range(len(data[:n])):
                if "|move|" in data[n - i]:
                    killer = data[n - i].split("|")[2]
                    nickname_search = self.nickname_marker(killer)
                    killer = nicknames[nickname_search]

                    if not mon.split(":")[0][:-1] == nickname_search.split(":")[0]:
                        # add kill count
                        kd = self.add_kill(kd, nickname_search, True)

                        # add kill cause
                        move = data[n - i].split("|")[3]
                        kills.append(pokemon + " was ko'd by " +
                                     killer + " using " + move)
                    break
        else:
            kd, kills = self.check_indirect(data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_indirect(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        # gmax residuals
        residuals = ["G-Max Volcalith", "G-Max Vine Lash",
                     "G-Max Cannonade", "G-Max Wildire"]
        trap_residuals = ["G-Max Sandblast", "G-Max Centiferno"]
        residual_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for residual in residuals:
            residual_markers.append(marker + residual)
        trapmarker = "|-damage|" + mon + "|0 fnt|[from] move: "
        for trap_residual in trap_residuals:
            residual_markers.append(trapmarker + trap_residual + "|[partiallytrapped]")
        for residual_marker in residual_markers:
            if residual_marker in data[:n]:
                effect = residual_marker.split("]")[1][1:]
                if "move:" in effect:
                    effect = effect.split(":")[1][1:]
                    effect = effect.split("|")[0]
                for i in range(len(data[:n])):
                    if searching and "|move|" in data[n - i] and effect in data[n - i]:
                        killer = data[n - i].split("|")[2]
                        opp = self.check_player(killer)
                        if opp != player:
                            searching = False
                            nickname_search = self.nickname_marker(killer)
                            killer = nicknames[nickname_search]

                            # add kill count
                            kd = self.add_kill(kd, nickname_search)

                            # add kill cause
                            kills.append(pokemon + " was ko'd by " +
                                         killer + "'s Gmax move residual effect")
                            break
        if searching:
            kd, kills = self.check_weather(data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_weather(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        # damaging weathers
        weathers = ["Hail", "Sandstorm"]
        weather_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for weather in weathers:
            weather_markers.append(marker + weather)
        for weather_marker in weather_markers:
            if weather_marker in data[:n]:
                effect = weather_marker.split("]")[1][1:]
                for i in range(len(data[:n])):
                    if searching and "|-weather|" + effect + "|[from] ability:" in data[n - i]:
                        killer = data[n - i].split("]")[2][1:]
                        opp = self.check_player(killer)
                        if opp != player:
                            searching = False
                            nickname_search = self.nickname_marker(killer)
                            killer = nicknames[nickname_search]

                            # add kill count
                            kd = self.add_kill(kd, nickname_search)

                            # add kill cause
                            kills.append(pokemon + " was ko'd by " +
                                         killer + "'s weather effect")
                            break
                    elif searching and "|-weather|" + effect in data[n - i] and "|-weather|" + effect + "|[upkeep]" != \
                            data[n - i]:
                        for j in range(len(data[:n - i])):
                            if searching and "|move|" in data[n - i - j]:
                                killer = data[n - i - j].split("|")[2]
                                opp = self.check_player(killer)
                                if opp != player:
                                    searching = False
                                    nickname_search = self.nickname_marker(killer)
                                    killer = nicknames[nickname_search]

                                    # add kill count
                                    kd = self.add_kill(kd, nickname_search)

                                    # add kill cause
                                    kills.append(pokemon + " was ko'd by " +
                                                 killer + "'s weather effect")
                                    break
        if searching:
            kd, kills = self.check_perish(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_perish(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        # Perish Song Marker
        marker = "|-start|" + mon + "|perish0"
        if marker in data[:n]:
            for i in range(len(data[:n])):
                if "|move|" in data[n - i] and "Perish Song" in data[n - i]:
                    killer = data[n - i].split("|")[2]
                    opp = self.check_player(killer)
                    nickname_search = self.nickname_marker(killer)
                    killer = nicknames[nickname_search]

                    if opp != player:
                        # add kill count
                        kd = self.add_kill(kd, nickname_search)

                        # add kill cause
                        move = data[n - i].split("|")[3]
                        kills.append(pokemon + " was ko'd by " +
                                     killer + " using " + move)
                    break
        else:
            kd, kills = self.check_destiny_bond(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_destiny_bond(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        if "|-activate|" in data[n - 1] and "move: Destiny Bond" in data[n - 1]:
            killer = data[n - 1].split("|")[2]
            opp = self.check_player(killer)
            nickname_search = self.nickname_marker(killer)
            killer = nicknames[nickname_search]

            if opp != player:
                # add kill count
                kd = self.add_kill(kd, nickname_search, True)

                # add kill cause
                move = data[n - 1].split("|")[3].split(":")[1][1:]
                kills.append(pokemon + " was ko'd by " +
                             killer + " using " + move)
        else:
            kd, kills = self.check_status(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_status(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        statuses = ["brn", "psn"]
        status_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for status in statuses:
            status_markers.append(marker + status)
        for status_marker in status_markers:
            if status_marker in data[:n]:
                effect = status_marker.split("]")[1][1:]
                for i in range(len(data[:n])):
                    if searching and "|-status|" + mon + "|" + effect + "|[from] ability:" in data[n - i]:
                        killer = data[n - i].split("]")[2][1:]
                        opp = self.check_player(killer)
                        if opp != player:
                            searching = False
                            nickname_search = self.nickname_marker(killer)
                            killer = nicknames[nickname_search]

                            # add kill count
                            kd = self.add_kill(kd, nickname_search)

                            # add kill cause
                            kills.append(pokemon + " was ko'd by status from " +
                                         killer + "'s ability")
                            break
                    elif searching and ("|-status|" + mon + "|" + effect in data[n - i] or (
                            effect == "psn" and "|-status|" + mon + "|" + "tox" in data[n - i])):
                        if "|move|" in data[n - i - 1]:
                            killer = data[n - i - 1].split("|")[2]
                            opp = self.check_player(killer)

                            if opp != player:
                                searching = False
                                nickname_search = self.nickname_marker(killer)
                                killer = nicknames[nickname_search]

                                # add kill count
                                kd = self.add_kill(kd, nickname_search)

                                # add kill cause
                                move = data[n - i - 1].split("|")[3]
                                kills.append(pokemon + " was ko'd by status from " +
                                             killer + " using " + move)
                                break
                        elif "|-damage|" + mon in data[n - i - 1] or "|-damage|" + mon in data[n - i - 2]:
                            for j in range(len(data[:n - i])):
                                if searching and "|move|" in data[n - i - j]:
                                    killer = data[n - i - j].split("|")[2]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search)

                                        # add kill cause
                                        move = data[n - i - j].split("|")[3]
                                        kills.append(pokemon + " was ko'd by status side effect from " +
                                                     killer + "'s " + move)
                                        break
                        elif "|-activate|" in data[n - i - 1]:
                            killer = data[n - i - 1].split("|")[2]
                            opp = self.check_player(killer)

                            if opp != player:
                                searching = False
                                nickname_search = self.nickname_marker(killer)
                                killer = nicknames[nickname_search]

                                # add kill count
                                kd = self.add_kill(kd, nickname_search)

                                # add kill cause
                                kills.append(pokemon + " was ko'd by status from interaction with " +
                                             killer)
                                break
                        elif "|switch|" + mon in data[n - i - 1] or "|switch|" + mon in data[n - i - 2]:
                            for j in range(len(data[:n - i])):
                                if searching and "|move|" in data[n - i - j] and "Toxic Spikes" in data[n - i - j]:
                                    killer = data[n - i - j].split("|")[2]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search)

                                        # add kill cause
                                        move = data[n - i - j].split("|")[3]
                                        kills.append(pokemon + " was ko'd by status side effect from " +
                                                     killer + "'s " + move)
                                        break
        if searching:
            kd, kills = self.check_hazards(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)

        return kd, kills

    def check_hazards(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        hazards = ["Spikes", "Stealth Rock"]
        hazard_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for hazard in hazards:
            hazard_markers.append(marker + hazard)
        for hazard_marker in hazard_markers:
            if hazard_marker in data[:n]:
                effect = hazard_marker.split("]")[1][1:]
                for i in range(len(data[:n])):
                    if hazard_marker in data[n-i]:
                        for j in range(len(data[:n-i])):
                            if searching and "|move|" in data[n-i-j] and effect in data[n-i-j]:
                                killer = data[n-i-j].split("|")[2]
                                opp = self.check_player(killer)
                                nickname_search = self.nickname_marker(killer)
                                killer = nicknames[nickname_search]

                                if opp != player:
                                    searching = False

                                    # add kill count
                                    kd = self.add_kill(kd, nickname_search)

                                    # add kill cause
                                    move = data[n-i-j].split("|")[3]
                                    kills.append(pokemon + " was ko'd by " +
                                                 killer + "'s entry hazard " + move)
                                break
        if searching:
            kd, kills = self.check_items(data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_items(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        # Including Rough Skin ability because it is so similar to the Rocky Helmet effect
        items = ["item: Rocky Helmet", "item: Sticky Barb", "ability: Rough Skin"]
        item_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for item in items:
            item_markers.append(marker + item)
        for item_marker in item_markers:
            if any(item_marker in line for line in data[:n]):
                effect = item_marker.split("]")[1][1:].split("|")[0]
                for i in range(len(data[:n])):
                    if item_marker in data[n - i]:
                        if searching and effect == "item: Rocky Helmet" or effect == "ability: Rough Skin":
                            killer = data[n - i].split("]")[2][1:]
                            opp = self.check_player(killer)
                            if opp != player:
                                searching = False
                                nickname_search = self.nickname_marker(killer)
                                killer = nicknames[nickname_search]

                                # add kill count
                                kd = self.add_kill(kd, nickname_search)

                                # add kill cause
                                kills.append(pokemon + " was ko'd by recoil from " +
                                             killer + "'s Rocky Helmet or Rough Skin")
                                break
                        elif searching and effect == "item: Sticky Barb":
                            if ("|-item|" + mon + "|Sticky Barb|[from] move: Trick" in data[:n] or
                                    "|-item|" + mon + "|Sticky Barb|[from] move: Switcheroo" in data[:n]):
                                for j in range(len(data[:n - i])):
                                    if (searching and "|move|" in data[n-i-j] and "Trick" in data[n-i-j] or
                                            "Switcheroo" in data[n - i - j]):
                                        killer = data[n - i - j].split("|")[2]
                                        opp = self.check_player(killer)
                                        if opp != player:
                                            searching = False
                                            nickname_search = self.nickname_marker(killer)
                                            killer = nicknames[nickname_search]

                                            # add kill count
                                            kd = self.add_kill(kd, nickname_search)

                                            # add kill cause
                                            kills.append(pokemon + " was ko'd by damage from " +
                                                         killer + "'s Tricked/Switcheroo'd Sticky Barb")
                                            break
                            else:
                                searching = False
                                kills.append(
                                    pokemon + "was ko'd by damage from Sticky Barb. Please manually verify whether "
                                              "this Sticky Barb originated from the opponent, and thus whether a "
                                              "Indirect Kill should be awarded to the original holder.")
        if searching:
            kd, kills = self.check_traps(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_traps(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        residual_markers = []
        trapmarker = "|-damage|" + mon + "|0 fnt|[from] move: "
        trap_residuals = ["Bind", "Clamp", "Fire Spin", "Magma Storm", "Sand Tomb", "Whirlpool", "Wrap"]
        for trap_residual in trap_residuals:
            residual_markers.append(trapmarker + trap_residual + "|[partiallytrapped]")
        for residual_marker in residual_markers:
            if residual_marker in data[:n]:
                effect = residual_marker.split("]")[1][1:]
                if "move:" in effect:
                    effect = effect.split(":")[1][1:]
                    effect = effect.split("|")[0]
                for i in range(len(data[:n])):
                    if searching and "|move|" in data[n - i] and effect in data[n - i]:
                        killer = data[n - i].split("|")[2]
                        opp = self.check_player(killer)
                        if opp != player:
                            searching = False
                            nickname_search = self.nickname_marker(killer)
                            killer = nicknames[nickname_search]

                            # add kill count
                            kd = self.add_kill(kd, nickname_search)

                            # add kill cause
                            kills.append(pokemon + " was ko'd by " +
                                         killer + "'s trapping move residual effect")
                            break
        if searching:
            kd, kills = self.check_misc(
                data, mon, pokemon, n, nicknames, kd, kills, searching, player)
        return kd, kills

    def check_misc(self, data, mon, pokemon, n, nicknames, kd, kills, searching, player):
        miscs = ["Curse", "Leech Seed", "Nightmare", "ability: Bad Dreams", "pokemon: Mimikyu-Busted",
                 "ability: Liquid Ooze", "ability: Aftermath",
                 "item: Jaboca Berry", "item: Rowap Berry", "Fire Pledge", "Grass Pledge", "ability: Innards Out",
                 "ability: Gulp Missile"]
        misc_markers = []
        marker = "|-damage|" + mon + "|0 fnt|[from] "
        for misc in miscs:
            misc_markers.append(marker + misc)
        for misc_marker in misc_markers:
            if any(misc_marker in line for line in data[:n]):
                effect = misc_marker.split("]")[1][1:].split("|")[0]
                for i in range(len(data[:n])):
                    if misc_marker in data[n - i]:
                        if searching and effect == "Curse":
                            for j in range(len(data[:n - i])):
                                if searching and "|-start|" in data[n - i - j] and "Curse" in data[n - i - j]:
                                    killer = data[n - i - j].split("]")[1][1:]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search)

                                        # add kill cause
                                        kills.append(pokemon + " was ko'd by nightmare from " +
                                                     killer + "'s Curse")
                                        break
                        elif searching and effect == "Leech Seed":
                            for j in range(len(data[:n - i])):
                                if searching and "|-start|" in data[n - i - j] and "Leech Seed" in data[n - i - j]:
                                    killer = data[n - i - j - 1].split("|")[2]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search)

                                        # add kill cause
                                        kills.append(pokemon + " was ko'd by leeching from " +
                                                     killer + "'s Leech Seed")
                                        break
                        elif searching and "item" in effect or "ability" in effect:
                            killer = data[n - i].split("]")[2][1:]
                            opp = self.check_player(killer)
                            if opp != player:
                                searching = False
                                nickname_search = self.nickname_marker(killer)
                                killer = nicknames[nickname_search]

                                # add kill count
                                kd = self.add_kill(kd, nickname_search)

                                # add kill cause
                                if "ability" in effect:
                                    kills.append(pokemon + " was ko'd by damage from " +
                                                 killer + "'s ability")
                                else:
                                    kills.append(pokemon + " was ko'd by recoil from " +
                                                 killer + "'s Berry")
                                break
                        elif (searching and effect == "Nightmare" or effect == "Fire Pledge" or
                                effect == "pokemon: Mimikyu-Busted"):
                            for j in range(len(data[:n - i])):
                                if searching and "|move|" in data[n - i - j] and effect in data[n - i - j]:
                                    killer = data[n - i - j].split("|")[2]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search)

                                        # add kill cause
                                        kills.append(pokemon + " was ko'd by residual from " +
                                                     killer + "'s " + effect)
                                        break
                                elif searching and "|move|" in data[n - i - j] and effect == "pokemon: Mimikyu-Busted":
                                    killer = data[n - i - j].split("|")[2]
                                    opp = self.check_player(killer)
                                    if opp != player:
                                        searching = False
                                        nickname_search = self.nickname_marker(killer)
                                        killer = nicknames[nickname_search]

                                        # add kill count
                                        kd = self.add_kill(kd, nickname_search, True)

                                        # add kill cause
                                        kills.append(pokemon + " was ko'd by Disguise bust from " +
                                                     killer + "'s move")
                                        break
        return kd, kills
