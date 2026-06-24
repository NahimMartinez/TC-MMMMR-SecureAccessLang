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

Además de verificar si cada caso es válido o inválido, este runner
genera una sección adicional:

    - Árboles sintácticos (AST) para todos los casos válidos.
    - Reporte detallado de errores para todos los casos inválidos.

    Esto permite evidenciar que el parser no solo acepta o rechaza entradas,
    sino que también construye correctamente la representación sintáctica
    interna de los programas válidos.
=============================================================================
"""

import sys
from parser import parse


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

            casos.append((entrada, esperado))

    return casos


def ejecutar_casos(casos):
    """
    Ejecuta el parser sobre cada caso y compara el resultado real contra
    el esperado.

    Devuelve:
        total
        aciertos
        fallos

        arboles_validos:
            lista de tuplas (entrada, ast)

        errores_invalidos:
            lista de tuplas (entrada, mensaje_error)

    Estas dos últimas estructuras permiten generar posteriormente
    una sección específica con los árboles sintácticos construidos
    y otra con los errores detectados correctamente.
    """

    aciertos = 0
    fallos = []

    # ------------------------------------------------------------------
    # Casos válidos:
    # se almacenan para imprimir el AST al final.
    # ------------------------------------------------------------------
    arboles_validos = []

    # ------------------------------------------------------------------
    # Casos inválidos:
    # se almacena el mensaje de error producido por el parser.
    # ------------------------------------------------------------------
    errores_invalidos = []

    for entrada, esperado in casos:

        try:
            ast = parse(entrada)

            obtenido = 'VALIDO'
            detalle = repr(ast)

            # Guardar árbol solamente para casos que debían ser válidos
            if esperado == 'VALIDO':
                arboles_validos.append((entrada, ast))

        except SyntaxError as e:

            obtenido = 'INVALIDO'
            detalle = str(e)

            # Guardar error solamente para casos que debían ser inválidos
            if esperado == 'INVALIDO':
                errores_invalidos.append((entrada, detalle))

        if obtenido == esperado:
            aciertos += 1
            estado = 'OK'
        else:
            estado = 'FALLO'
            fallos.append((entrada, esperado, obtenido, detalle))

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(
            f"[{estado}] {entrada_mostrar!r:60s} "
            f"esperado={esperado:9s} obtenido={obtenido}"
        )

    return (
        len(casos),
        aciertos,
        fallos,
        arboles_validos,
        errores_invalidos
    )


def imprimir_arboles(arboles_validos):
    """
    Muestra todos los árboles sintácticos generados para los casos válidos.

    Esta sección sirve como evidencia de que el parser no solo acepta
    las entradas correctas, sino que además construye correctamente
    el AST correspondiente.
    """

    print("\n" + "=" * 70)
    print("ARBOLES GENERADOS (CASOS VALIDOS)")
    print("=" * 70)

    for entrada, ast in arboles_validos:

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(f"\nEntrada: {entrada_mostrar!r}")
        print()

        # El __repr__ del Node ya imprime el árbol con sangría
        print(ast)


def imprimir_errores(errores_invalidos):
    """
    Muestra los errores detectados para los casos inválidos.

    Esta sección permite demostrar que el parser identifica correctamente
    las violaciones a la gramática y produce mensajes descriptivos.
    """

    print("\n" + "=" * 70)
    print("CASOS INVALIDOS")
    print("=" * 70)

    for entrada, error in errores_invalidos:

        entrada_mostrar = entrada.replace('\n', '\\n')

        print(f"\nEntrada: {entrada_mostrar!r}")
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
        arboles_validos,
        errores_invalidos
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

        for entrada, esperado, obtenido, detalle in fallos:

            entrada_mostrar = entrada.replace('\n', '\\n')

            print(f"  Entrada:  {entrada_mostrar!r}")
            print(f"  Esperado: {esperado}")
            print(f"  Obtenido: {obtenido}")
            print(f"  Detalle:  {detalle}")
            print()

    # ------------------------------------------------------------------
    # NUEVA SECCIÓN:
    # Mostrar los árboles sintácticos generados.
    # ------------------------------------------------------------------
    imprimir_arboles(arboles_validos)

    # ------------------------------------------------------------------
    # NUEVA SECCIÓN:
    # Mostrar los errores detectados para casos inválidos.
    # ------------------------------------------------------------------
    imprimir_errores(errores_invalidos)

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