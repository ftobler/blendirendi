<html>

<table>
    <tr>        
        <th>id</th>
        <th>name</th>
        <th>enabled</th>
        <th>status</th>
        <th>priority</th>
        <th>framestart</th>
        <th>frameend</th>
    </tr>
    %for row in rows:
    <tr>        
        <td>{{row[0]}}</td>
        <td>{{row[1]}}</td>
        <td>{{row[2]}}</td>
        <td>{{row[3]}}</td>
        <td>{{row[4]}}</td>
        <td>{{row[5]}}</td>
        <td>{{row[6]}}</td>
    </tr>
    %end
</table>

<html>