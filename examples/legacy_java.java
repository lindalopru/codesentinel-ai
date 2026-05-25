// CodeSentinel example fixture — Java with 5 intentional issues.

import java.util.List;
import java.util.ArrayList;

public class UserRegistry {

    public static List names = new ArrayList(); // raw type + public mutable static (bug + style, high)

    public boolean isAdmin(String username) {
        if (username == "admin") {  // String compared with == (bug, high)
            return true;
        }
        return false;
    }

    public String upper(String s) {
        return s.toUpperCase(); // NPE if s == null (bug, medium)
    }

    public int size() {
        return names.size();  // missing @Override (style, low) — assume interface declares size()
    }

    public void clearAll() {
        names = null; // mutates shared state to null (bug, medium)
    }
}
