import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** Randomised greedy for the 0/1 knapsack problem (Java end-to-end test of
 * irace-evo): each restart adds items in an order biased by score(). Prints
 * the best total value found. */
public class Knapsack {
    // How attractive an item is; the method irace-evo may rewrite.
    static double score(int value, int weight, int capacityLeft) {
        return (double) value / weight;
    }

    static int construct(int[][] items, int capacity, double alpha, Random rng) {
        int left = capacity, total = 0;
        boolean[] chosen = new boolean[items.length];
        while (true) {
            List<Integer> fits = new ArrayList<>();
            for (int i = 0; i < items.length; i++) {
                if (!chosen[i] && items[i][1] <= left) fits.add(i);
            }
            if (fits.isEmpty()) return total;
            final int cap = left;
            fits.sort((a, b) -> Double.compare(score(items[b][0], items[b][1], cap), score(items[a][0], items[a][1], cap)));
            int pick = fits.get(rng.nextInt(Math.max(1, (int) (alpha * fits.size()))));
            chosen[pick] = true;
            left -= items[pick][1];
            total += items[pick][0];
        }
    }

    public static void main(String[] args) throws Exception {
        String file = null;
        double alpha = 0.3;
        int restarts = 20;
        long seed = 1;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "-i": file = args[++i]; break;
                case "--alpha": alpha = Double.parseDouble(args[++i]); break;
                case "--restarts": restarts = Integer.parseInt(args[++i]); break;
                case "--seed": seed = Long.parseLong(args[++i]); break;
            }
        }
        int[][] items;
        int capacity;
        try (BufferedReader in = new BufferedReader(new FileReader(file))) {
            String[] head = in.readLine().trim().split("\\s+");
            int n = Integer.parseInt(head[0]);
            capacity = Integer.parseInt(head[1]);
            items = new int[n][2];
            for (int i = 0; i < n; i++) {
                String[] p = in.readLine().trim().split("\\s+");
                items[i][0] = Integer.parseInt(p[0]);
                items[i][1] = Integer.parseInt(p[1]);
            }
        }
        Random rng = new Random(seed);
        int best = 0;
        for (int r = 0; r < restarts; r++) best = Math.max(best, construct(items, capacity, alpha, rng));
        System.out.println(best);
    }
}
