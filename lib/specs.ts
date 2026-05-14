/**
 * Деление характеристик товара на "ключевые" (показываются над описанием)
 * и "остальные" (под описанием).
 *
 * Приоритет универсальный для электроники: сначала идут спеки из PRIORITY_KEYS
 * в порядке списка, затем — все остальные в исходном порядке. Берём первые 9
 * для primary, остальное — secondary.
 */

const PRIORITY_KEYS: string[] = [
  // Память
  'Объём встроенной памяти',
  'Объем встроенной памяти',
  'Объём накопителя',
  'Объем накопителя',
  'Оперативная память',
  // Цвет
  'Цвет',
  'Цвет корпуса',
  // Экран
  'Диагональ экрана',
  'Экран',
  'Тип экрана',
  'Размер корпуса',
  // Тип устройства (наушники, часы)
  'Тип',
  // Чип
  'Процессор',
  // Камера
  'Основная камера',
  // Звук/шумодав
  'Активное шумоподавление',
  'Шумоподавление',
  // Аккумулятор / время работы
  'Время работы',
  'Емкость аккумулятора',
  'Ёмкость аккумулятора',
  'Аккумулятор',
  // ОС
  'Операционная система',
  // Год
  'Год релиза',
  // Защита
  'Класс водонепроницаемости',
  // Материал
  'Материал корпуса',
  'Материал ремешка',
  // Совместимость
  'Совместимость',
  // Прочее ключевое
  'Вес (грамм)',
  'Размеры',
]

export const PRIMARY_LIMIT = 9

export type SpecPair = [string, string]

export function splitSpecs(specs: Record<string, string> | null | undefined): {
  primary: SpecPair[]
  secondary: SpecPair[]
} {
  if (!specs) return { primary: [], secondary: [] }

  const all = Object.entries(specs)
  if (all.length === 0) return { primary: [], secondary: [] }

  const taken = new Set<string>()
  const primary: SpecPair[] = []

  for (const key of PRIORITY_KEYS) {
    if (primary.length >= PRIMARY_LIMIT) break
    if (key in specs && !taken.has(key)) {
      primary.push([key, specs[key]])
      taken.add(key)
    }
  }

  // Если приоритетных не хватает — добираем из остальных по порядку
  if (primary.length < PRIMARY_LIMIT) {
    for (const [k, v] of all) {
      if (primary.length >= PRIMARY_LIMIT) break
      if (!taken.has(k)) {
        primary.push([k, v])
        taken.add(k)
      }
    }
  }

  const secondary: SpecPair[] = all.filter(([k]) => !taken.has(k))
  return { primary, secondary }
}
