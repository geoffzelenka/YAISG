# Yet Another Idle Skilling Game

Multiplayer, web-based game where a player can skill up multiple skills in real time.  Similar games in this genre are Melvor Idle, Idle Clans, and Ironwood RPG.

Differentiator of this game is that the player can choose different realms to setup their estate.  Different realms provide different resources and may have modifiers to skillup rates.  The player can contribute resources to their estate and realm to improve it as very-long term goal. 

Features:
Different skills:
1. gathering
2. refining
3. crafting
4. combat
5. exploration
Setup your own estate
* Choose a realm to reside and improve
Player driven marketplace

Backend design:
Login microservice to handle auth and sessions
Choose between python or golang to provide a RESTful API to serve the player client.
A sql backend to store state, sqlite first, if we need more features or scaling move to postgresql




Client design:
Choose a js framework that can handle a few frames and timers
The client will have a left side menu bar with a things the player can do, the client will pull available actions to populate that menu from the server. 
* Profile: general character stats, estate and realm overview
* Player Market: place to buy and sell resources among players
* Realm Market: buy and sell resources to the local realm
* Estate: actions for the player estate
* divider
* Combat section
* divider
* Skill lists:
  1. Gathering
  2. Refining
  3. Crafting
  4. exploration

Skilling work flows:

A player may only work on combat or a skill at a time, selecting a skill will request to begin that skill, the server will respond if the player can do that skill and the timer for 1 cycle of that skill will take.  Once that cycle completes, that client will request rewards for that skill cycle, and the server will respond if the rewards are ready and if so, the rewards.

Completed skill cycles will reward skill xp and possibly other resource rewards.
