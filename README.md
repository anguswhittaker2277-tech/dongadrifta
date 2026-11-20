# Donga Drifta

Wingfield yard free-roam game. Open the live site, or index.html.

## Sound credits

The metal crash sounds are cut from recordings by **Halleck** on Freesound
(metal medium hit, metal hits medium 1, metal hits light 1, metal thump, big metal side impact 1 and 2, metal crash 1:
freesound.org/people/Halleck), edited by **CryHam** for the game Stunt Rally (stuntrally.tuxfamily.org),
licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). They were level-matched and converted to MP3 here.

These are public domain ([CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)); credited anyway, with thanks:

- Water splashes (the cold tub, driving through water): splashes 03, 04, 05, 09, 11 and 14 from
  [40 CC0 water splash & slime SFX](https://opengameart.org/content/40-cc0-water-splash-slime-sfx) by **rubberduck**.
- Chopping and splitting wood, the tree falling: wood hits and wood 01–04 from
  [100 CC0 SFX #2](https://opengameart.org/content/100-cc0-sfx-2) by **rubberduck**; chop and creaks from
  [RPG Audio](https://kenney.nl/assets/rpg-audio) and heavy wood impacts from [Impact Sounds](https://kenney.nl/assets/impact-sounds) by **Kenney**.
- The bunks burning: [Fireplace Sound loop](https://opengameart.org/content/fireplace-sound-loop) by **PagDev**
  (one layer pitched down for the roar under one as recorded, looped), and pops cut from
  [Fire Crackling](https://opengameart.org/content/fire-crackling) by **AntumDeluge**.
- Everyday sounds, all from Freesound (freesound.org/s/&lt;number&gt;):
  - footsteps and shovelled dirt: Footsteps_6_Dirt_shoe (353799) by **monte32**;
  - explosions: Explosion_01 (235968) by **tommccann** and bad explosion (47252) by a deleted user;
  - thuds: BODY FALL - V HVY - DIRT (504626) by **leonelmail** and Body fall_01 (346695) by a deleted user;
  - breaking: Crack of branch 3 (164472) by a deleted user and Twig Snap (364699) by **alegemaate**;
  - punches: Realistic Punch (244513) by **JewTwinz** and Punch_1-2 (94778) by **taylorsyoung**;
  - swings: Whoosh (60013) and SWOSH-01 (59988) by **qubodup**, and Swing Woosh (389590) by **Jofae**;
  - doors:
    - car door close (208695) by **monotraum**;
    - car_door_closed (9876) by **Heigh-hoo**;
    - Car Door Handle (50697) by **RutgerMuller**;
    - Car_Door-Open_bulky (86229) by **nmscher**;
    - Truck door closed. (538947) by **SubwaySandwitch420**;
  - starter motors: 1970 VW Bug Engine Cranking 2 (579213) by **bowlingballout** and tractor-engine-start (256808) by **radwoc**;
  - Bike Bell (81875) by **bsumusictech**;
  - chimes:
    - bell ding 1 (611113) by **5ro4**;
    - service bell ring (221515) by **AlaskaRobotics**;
    - ding 3 (149268) by **organicmanpl**;
    - Ringing bell - happy (116779) by **domrodrig**;
  - microwave beep (242006) by **photogtony**;
  - hisses: Steam (398077) by **SukritSen** and air_brakes_loud_fade_out (504865) by **rabbydaw**.

They were trimmed, layered, compressed and level-matched, and converted to MP3 here.

## Voice credits

Madman's, the backpackers' and Dima's voices were generated with [Kokoro-82M](https://github.com/hexgrad/kokoro)
(Apache-2.0), using phonemes from espeak-ng. See `tools/voices/README.md` for how the voice pack is made.
Matt's voice was made in Voicebox from his own voice profile (the recordings are in `tools/voices/rec_mt/`).

## Libraries

Loaded from jsDelivr: [three.js](https://threejs.org) (MIT), [three-mesh-bvh](https://github.com/gkjohnson/three-mesh-bvh) (MIT),
and [meshoptimizer](https://github.com/zeux/meshoptimizer) (MIT, by Arseny Kapoulkine), which works out the lighter far-off
versions of the scan in the background once the game's running.
