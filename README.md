# Discord.py Music Bot
A fully functional discord music bot. All codes are given here. This is pretty advanced coding. It is recommended to get a upperhand on *discord.py* development before watching or using this code.

## Requirements
* This bot uses ***Lavalink***. So it is required to run lavalink before runnig this bot.
* Lavalink player configuration file is also needed. You can get that from [here](https://github.com/BLAK3STORM/Singing_Chimken_Bot/tree/master/config). Keep the ***application.yml*** in the ***Lavalink.jar*** root directory.
* ***Wavelink*** python module is also required to link the bot to the lavalink player. But all wavelink versions may not work. I recommend to use *wavelink v0.9*.
Use the command below to install wavelink v0.9:  
```pip3 install wavelink<1```
* Other usual discord.py libraries like *discord*, *discord.py*, *discord.py[voice]* etc are also recommended to have installed.

## About LAVALINK
Lavalink is a standalone program which is written in **Java**. It is a lightweight solution for playing musics from sources like **Youtube** or **Soundcloud**. It can handle hundreads of concurrent streams & supports sharding.

As lavalink is written in java, a **JDK** is required to run it. Download **OpenJDK** from [here](https://www.oracle.com/java/technologies/downloads/).

Download *Lavalink* from [here](https://ci.fredboat.com/viewLog.html?buildId=lastSuccessful&buildTypeId=Lavalink_Build&tab=artifacts&guest=1).

Everytime before running the bot lavalink will be required to run. Use the following command to do so:
```java -jar lavalink_path/Lavalink.jar```
