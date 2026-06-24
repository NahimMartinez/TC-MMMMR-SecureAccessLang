"""
=============================================================================
TEST RUNNER — SecureAccessLang
=============================================================================
Lee el archivo casos_prueba.txt (formato: ENTRADA | RESULTADO_ESPERADO),
ejecuta el parser sobre cada entrada y compara el resultado obtenido con el
esperado. Reporta un resumen final con coincidencias y discrepancias.

Esto separa los DATOS de prueba (casos_prueba.txt) de la LÓGICA de prueba
(este script) y del propio parser (parser.py), siguiendo el principio de
diseño modular pedido por la cátedra.

Uso:
    python test_runner.py
    python test_runner.py otro_archivo_de_casos.txt

Además de verificar la clasificación de cada caso, este runner genera dos
secciones adicionales:

    - Árboles sintácticos (AST) para todos los casos válidos o parciales.
    - Reporte detallado de errores para los casos inválidos o parciales.

    Esto permite evidenciar que el parser no solo acepta o rechaza entradas,
    sino que además construye correctamente la representación sintáctica
    interna de los programas, incluso cuando se recupera de errores
    intermedios dentro de una misma entrada.

-----------------------------------------------------------------------------
SOBRE LA CLASIFICACIÓN VALIDO / INVALIDO / PARCIAL
-----------------------------------------------------------------------------
parse() ahora devuelve siempre una tupla (ast, errores), reflejando que el
parser hace recuperación de errores en modo pánico: una sola entrada puede
contener varias sentencias, algunas válidas y otras no. Por eso la antigua
clasificación binaria (VALIDO/INVALIDO, antes determinada por si parse()
lanzaba o no una excepción) ya no alcanza para describir el resultado.
Se usan tres categorías:

    VALIDO    -> 0 errores. Todas las sentencias de la entrada son correctas.
    PARCIAL   -> al menos 1 error, pero también al menos 1 sentencia válida
                 reconocida. El parser se recuperó y continuó el análisis.
    INVALIDO  -> al menos 1 error y NINGUNA sentencia válida reconocida.
                 Equivalente a lo que antes era el único caso de fallo.

IMPORTANTE: esto es distinto de la "recuperación" aparente que se obtenía
simplemente por el hecho de que este runner llama a parse() una vez por
cada línea de casos_prueba.txt. Esa repetición de llamadas NO es
recuperación de errores: cada llamada es independiente y el parser arranca
de cero. La recuperación real ocurre DENTRO de una misma llamada a parse(),
cuando una entrada con múltiples sentencias tiene un error en alguna de
ellas y el parser continúa analizando las siguientes. Por eso
casos_prueba.txt incluye casos PARCIAL que integran varias sentencias en
una sola entrada con un error intermedio: solo así se ejercita la
recuperación real y no el efecto óptico de "una corrida por caso".
=============================================================================
"""

import sys
from parser import parse


RESULTADOS_VALIDOS = {'VALIDO', 'INVALIDO', 'PARCIAL'}


def cargar_casos(ruta):
    """
    Lee el archivo de casos de prueba y devuelve una lista de tuplas
    (entrada, resultado_esperado).

    Ignora líneas vacías y comentarios (#). Decodifica la secuencia "\\n"
    como salto de línea real, para permitir probar programas con múltiples
    sentencias en una sola línea del archivo.
    """
    casos = []

    with open(ruta, encoding='utf-8') as f:
        for num_linea, linea in enumerate(f, start=1):

            linea = linea.rstrip('\n')

            # Ignorar comentarios y líneas vacías
            if not linea.strip() or linea.strip().startswith('#'):
                continue

            # Validar formato
            if '|' not in linea:
                print(
                    f"  [Aviso] Línea {num_linea} del archivo de casos "
                    f"ignorada (formato inválido): {linea!r}"
                )
                continue

            entrada, esperado = linea.rsplit('|', 1)

            entrada = entrada.strip().replace('\\n', '\n')
            esperado = esperado.strip().upper()

            if esperado not in RESULTADOS_VALIDOS:
                print(
                    f"  [Aviso] Línea {num_linea}: resultado esperado "
                    f"'{esperado}' no reconocido (use VALIDO, INVALIDO o "
                    f"PARCIAL). Caso ignorado."
                )
                continue

            casos.append((entrada, esperado))

    return casos


def clasificar(ast, errores):
    """
    Determina la categoría de un resultado de parse() según la cantidad de
    errores recuperados y la cantidad de sentencias válidas reconocidas.

        VALIDO   -> sin errores.
        PARCIAL  -> con errores, pero con al menos una sentencia válida
                    (el parser se recuperó y reconoció parte del programa).
        INVALIDO -> con errores y sin ninguna sentencia válida reconocida.
    """
    if not errores:
        return 'VALIDO'

    sentencias_validas = ast.attrs.get('sentencias', [])
    if sentencias_validas:
        return 'PARCIAL'

    return 'INVALIDO'


def ejecutar_casos(casos):
    """
    Ejecuta el parser sobre cada caso y compara el resultado real contra
    el esperado.

    Devuelve:
        total
        aciertos
        fallos

        resultados_ast:
            lista de tuplas (entrada, esperado, obtenido, ast, errores)
            para todos los casos que produjeron al menos una sentencia
            válida (VALIDO o PARCIAL), para poder mostrar su AST.

        resultados_errores:
            lista de tuplas (entrada, esperado, obtenido, errores)
            para todos los casos que produjeron al menos un error
            (INVALIDO o PARCIAL), para poder mostrar los errores detectados
            y recuperados.
    """

    aciertos = 0
    fallos = []

    resultados_ast = []
    resultados_errores = []

    for entrada, esperado in casos:

        ast, errores = parse(entrada)
        obtenido = clasificar(ast, errores)

        if obtenido in ('VALIDO', 'PARCIAL'):
            resultados_ast.append((entrada, esperado, obtenido, ast, errores))

        if obtenido in ('INVALIDO', 'PARCIAL'):
            resultados_errores.append((entrada, esperado, obtenido, errores))

        if obtenido == esperado:
            aciertos += 1
            estado = 'OK'
        else:
            estado = 'FALLO'
            fallos.append((entrada, esperado, obtenido, repr(ast), errores))

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(
            f"[{estado}] {entrada_mostrar!r:60s} "
            f"esperado={esperado:9s} obtenido={obtenido}"
        )

    return (
        len(casos),
        aciertos,
        fallos,
        resultados_ast,
        resultados_errores
    )


def imprimir_arboles(resultados_ast):
    """
    Muestra los árboles sintácticos generados para los casos VALIDO y
    PARCIAL. Para los PARCIAL, el árbol mostrado es el AST parcial: solo
    contiene las sentencias que el parser logró reconocer tras recuperarse
    de los errores intermedios.

    Esta sección sirve como evidencia de que el parser no solo acepta
    las entradas correctas, sino que además construye correctamente
    el AST correspondiente, incluso de forma parcial.
    """

    print("\n" + "=" * 70)
    print("ARBOLES GENERADOS (CASOS VALIDOS Y PARCIALES)")
    print("=" * 70)

    for entrada, esperado, obtenido, ast, errores in resultados_ast:

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(f"\nEntrada: {entrada_mostrar!r}")
        print(f"Clasificación: {obtenido}")

        if obtenido == 'PARCIAL':
            print(f"(AST parcial — se omitieron {len(errores)} sentencia(s) con error)")

        print()

        # El __repr__ del Node ya imprime el árbol con sangría
        print(ast)


def imprimir_errores(resultados_errores):
    """
    Muestra los errores detectados (y recuperados, en el caso de PARCIAL)
    para los casos INVALIDO y PARCIAL.

    Esta sección permite demostrar que el parser identifica correctamente
    las violaciones a la gramática, produce mensajes descriptivos con línea,
    y en los casos PARCIAL continúa el análisis del resto de la entrada en
    lugar de abortar por completo.
    """

    print("\n" + "=" * 70)
    print("CASOS INVALIDOS Y PARCIALES (errores detectados)")
    print("=" * 70)

    for entrada, esperado, obtenido, errores in resultados_errores:

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(f"\nEntrada: {entrada_mostrar!r}")
        print(f"Clasificación: {obtenido}")
        for error in errores:
            print(f"  Detectado correctamente -> {error}")


def main():

    ruta = sys.argv[1] if len(sys.argv) > 1 else 'casos_prueba.txt'

    print("=" * 70)
    print(f"EJECUTANDO CASOS DE PRUEBA DESDE: {ruta}")
    print("=" * 70)

    casos = cargar_casos(ruta)

    (
        total,
        aciertos,
        fallos,
        resultados_ast,
        resultados_errores
    ) = ejecutar_casos(casos)

    print("\n" + "=" * 70)
    print(f"RESUMEN: {aciertos}/{total} casos correctos")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Si hubo discrepancias entre lo esperado y lo obtenido,
    # se reportan detalladamente.
    # ------------------------------------------------------------------
    if fallos:

        print(
            f"\n{len(fallos)} caso(s) con resultado distinto al esperado:\n"
        )

        for entrada, esperado, obtenido, detalle, errores in fallos:

            entrada_mostrar = entrada.replace('\n', '\\n')

            print(f"  Entrada:  {entrada_mostrar!r}")
            print(f"  Esperado: {esperado}")
            print(f"  Obtenido: {obtenido}")
            print(f"  AST:      {detalle}")
            print(f"  Errores:  {errores}")
            print()

    # ------------------------------------------------------------------
    # Mostrar los árboles sintácticos generados (VALIDO + PARCIAL).
    # ------------------------------------------------------------------
    imprimir_arboles(resultados_ast)

    # ------------------------------------------------------------------
    # Mostrar los errores detectados/recuperados (INVALIDO + PARCIAL).
    # ------------------------------------------------------------------
    imprimir_errores(resultados_errores)

    # ------------------------------------------------------------------
    # Código de salida:
    #
    # 0 -> todos los casos coincidieron con lo esperado.
    # 1 -> existe al menos una discrepancia.
    # ------------------------------------------------------------------
    if fallos:
        sys.exit(1)

    print("\nTodos los casos coinciden con el resultado esperado.")
    sys.exit(0)


if __name__ == '__main__':
    main()