from collections import Counter
import sys

def read_ppm(path):
    with open(path, 'rb') as f:
        def token():
            t = bytearray()
            while True:
                c = f.read(1)
                if not c:
                    if t: return t.decode()
                    raise EOFError("Fim inesperado do arquivo")
                if c == b'#' and not t:
                    while (c := f.read(1)) not in (b'', b'\n'):
                        pass
                    continue
                if c.isspace():
                    if t: return t.decode()
                    continue
                t.extend(c)

        if token() != 'P6':
            raise ValueError("Apenas P6 (PPM binário) é suportado.")
        w, h, maxval = int(token()), int(token()), int(token())
        if maxval > 255:
            raise ValueError("maxval > 255 (16 bits) não suportado.")
        return w, h, f.read(w * h * 3)

def main():
    if len(sys.argv) != 3:
        sys.exit("Uso: python3 diff.py <img1.ppm> <img2.ppm>")

    try:
        w1, h1, d1 = read_ppm(sys.argv[1])
        w2, h2, d2 = read_ppm(sys.argv[2])
    except Exception as e:
        sys.exit(f"Erro: {e}")

    if (w1, h1) != (w2, h2):
        sys.exit(f"Dimensões diferentes: {w1}x{h1} vs {w2}x{h2}")

    total = w1 * h1
    common = min(len(d1) // 3, len(d2) // 3, total)
    if common < total:
        print("Aviso: imagem incompleta (pixels faltantes contam como diferentes).")

    # separa os canais dos pixels que existem nas duas imagens
    n = common * 3
    r1, g1, b1 = d1[0:n:3], d1[1:n:3], d1[2:n:3]
    r2, g2, b2 = d2[0:n:3], d2[1:n:3], d2[2:n:3]

    # checagem: as imagens são realmente cinza (R=G=B)?
    for nome, r, g, b in ((sys.argv[1], r1, g1, b1), (sys.argv[2], r2, g2, b2)):
        nao_cinza = sum(1 for x, y, z in zip(r, g, b) if x != y or y != z)
        if nao_cinza:
            print(f"Aviso: {nome} tem {nao_cinza} pixels com R, G e B diferentes (não é cinza puro).")

    diff = sum(1 for p, q in zip(zip(r1, g1, b1), zip(r2, g2, b2)) if p != q)
    diff += total - common  # pixels ausentes contam como diferença

    print(f"Resolução : {w1}x{h1}")
    print(f"Pixels    : {total}")
    print(f"Diferentes: {diff} ({diff / total * 100:.4f}%)")

    from collections import Counter

    linhas = Counter()
    exemplos = []
    for i in range(total):
        a = d1[i*3:i*3+3]
        b = d2[i*3:i*3+3]
        if a != b:
            y, x = divmod(i, w1)
            linhas[y] += 1
            if len(exemplos) < 15:
                exemplos.append((x, y, tuple(a), tuple(b)))

    for e in exemplos:
        print(e)
    print("Linhas afetadas:", len(linhas))

if __name__ == '__main__':
    main()