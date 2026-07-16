// Client-side dice engine - rolls are local to whoever clicks "Roll" for
// now (not broadcast to the table - that needs a shared roll log, which is
// a later phase's job). 5e RAW: a critical hit doubles the number of
// damage dice rolled, not the flat modifier - see rollDamage below.

export interface DamageRollResult {
  diceCount: number
  diceSides: number
  modifier: number
  crit: boolean
  dice: number[]
  total: number
}

export interface D20RollResult {
  advantage: 'normal' | 'advantage' | 'disadvantage'
  rolls: number[]
  chosen: number
  modifier: number
  total: number
  isCrit: boolean
  isFumble: boolean
}

function randomDie(sides: number): number {
  return 1 + Math.floor(Math.random() * sides)
}

export function rollDamage(diceCount: number, diceSides: number, modifier: number, crit: boolean): DamageRollResult {
  const rollCount = crit ? diceCount * 2 : diceCount
  const dice = Array.from({ length: rollCount }, () => randomDie(diceSides))
  const total = dice.reduce((sum, d) => sum + d, 0) + modifier
  return { diceCount, diceSides, modifier, crit, dice, total }
}

export function rollD20(modifier: number, advantage: D20RollResult['advantage'] = 'normal'): D20RollResult {
  const rolls = advantage === 'normal' ? [randomDie(20)] : [randomDie(20), randomDie(20)]
  const chosen = advantage === 'disadvantage' ? Math.min(...rolls) : Math.max(...rolls)
  return {
    advantage,
    rolls,
    chosen,
    modifier,
    total: chosen + modifier,
    isCrit: chosen === 20,
    isFumble: chosen === 1,
  }
}
